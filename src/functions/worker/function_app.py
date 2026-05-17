"""
function_app.py — Azure Function Worker
========================================
Blob Trigger : doc-storage/input/{name}
Service Bus Trigger : document-processing
Service Bus DLQ : document-processing/$DeadLetterQueue
"""

import logging
import os
import json
from datetime import datetime, timezone

import azure.functions as func

from shared.cosmos_client import get_job, patch_job
from shared.queue_message import parse_queue_message
from shared.servicebus_client import send_message
from shared.signalr_client import build_job_update_event, push_job_update
from shared.tagging import generate_tags

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = func.FunctionApp()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_blob_path(blob_name: str) -> tuple[str, str]:
    path = blob_name
    for prefix in ("doc-storage/", "input/"):
        if path.startswith(prefix):
            path = path[len(prefix):]
            break

    if path.startswith("input/"):
        path = path[len("input/"):]

    if "/" not in path:
        raise ValueError(f"Chemin blob invalide (format attendu input/<jobId>/<fileName>) : {blob_name}")

    document_id, file_name = path.split("/", 1)
    if not document_id or not file_name:
        raise ValueError(f"Chemin blob invalide (jobId ou fileName vide) : {blob_name}")

    return document_id, file_name


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _notify_job_update(
    pending: list[dict],
    document_id: str,
    status: str,
    message: str,
    tags: list | None = None,
) -> None:
    """REST immédiat ; output binding en secours si REST échoue."""
    if not push_job_update(document_id, status, message, tags):
        pending.append(build_job_update_event(document_id, status, message, tags))


# ---------------------------------------------------------------------------
# SignalR Negotiate
# ---------------------------------------------------------------------------
@app.route(route="negotiate", auth_level=func.AuthLevel.ANONYMOUS)
@app.generic_input_binding(
    arg_name="connectionInfo",
    type="signalRConnectionInfo",
    hubName="documents",
    connectionStringSetting="SIGNALR_CONNECTION_STRING"
)
def negotiate(req: func.HttpRequest, connectionInfo: str) -> func.HttpResponse:
    """
    Endpoint appelé par React pour obtenir le token d'accès SignalR.
    """
    origin = req.headers.get("Origin", "http://localhost:5173")
    cors_origin = origin if origin in (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ) else "http://localhost:5173"

    return func.HttpResponse(
        connectionInfo,
        status_code=200,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": cors_origin,
            "Access-Control-Allow-Credentials": "false",
        },
    )


# ---------------------------------------------------------------------------
# 1. Blob Trigger
# ---------------------------------------------------------------------------

@app.blob_trigger(
    arg_name="myblob",
    path="doc-storage/input/{name}",
    connection="docstorageprof_STORAGE",
)
@app.generic_output_binding(
    arg_name="signalRMessages",
    type="signalR",
    hubName="documents",
    connectionStringSetting="SIGNALR_CONNECTION_STRING",
)
def blob_upload_worker(myblob: func.InputStream, signalRMessages: func.Out[str]) -> None:
    raw_name: str = myblob.name or ""
    blob_size: int = myblob.length or 0

    logger.info("=" * 60)
    logger.info("[BlobTrigger] Nouveau blob détecté: %s", raw_name)

    pending_signalr: list[dict] = []

    try:
        document_id, file_name = _parse_blob_path(raw_name)
    except ValueError as exc:
        logger.error("[BlobTrigger] Parsing impossible — blob ignoré : %s", exc)
        return

    uploaded_at = _now_iso()
    try:
        patch_job(document_id, {
            "status": "UPLOADED",
            "size": blob_size,
            "uploadedAt": uploaded_at,
        })
        _notify_job_update(pending_signalr, document_id, "UPLOADED", "Fichier reçu")
    except Exception as exc:
        logger.error("[Cosmos] Échec mise à jour UPLOADED : %s", exc)

    try:
        patch_job(document_id, {"status": "QUEUED"})
        _notify_job_update(pending_signalr, document_id, "QUEUED", "Mis en file d'attente")
    except Exception as exc:
        logger.error("[Cosmos] Échec mise à jour QUEUED : %s", exc)

    if pending_signalr:
        signalRMessages.set(json.dumps(pending_signalr))

    message_payload = {
        "documentId": document_id,
        "fileName": file_name,
        "blobName": raw_name,
        "size": blob_size,
        "uploadedAt": uploaded_at,
    }

    try:
        send_message(message_payload)
        logger.info("[ServiceBus] Message envoyé")
    except Exception as exc:
        logger.error("[ServiceBus] Échec envoi message : %s", exc)
        try:
            patch_job(document_id, {
                "status": "ERROR",
                "errorMessage": f"ServiceBus send failed: {exc}",
                "errorAt": _now_iso(),
            })
        except Exception:
            pass
        return

    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# 2. Service Bus Trigger (Traitement IA)
# ---------------------------------------------------------------------------

@app.service_bus_queue_trigger(
    arg_name="azservicebus",
    queue_name="document-processing",
    connection="SERVICE_BUS_CONNECTION_STRING"
)
@app.generic_output_binding(
    arg_name="signalRMessages",
    type="signalR",
    hubName="documents",
    connectionStringSetting="SIGNALR_CONNECTION_STRING",
)
def service_bus_processing_worker(
    azservicebus: func.ServiceBusMessage,
    signalRMessages: func.Out[str],
) -> None:
    logger.info("=" * 60)
    logger.info("[ServiceBusTrigger] Réception d'un message")

    body = azservicebus.get_body().decode("utf-8")
    msg = parse_queue_message(body)

    document_id = msg["documentId"]
    file_name = msg["fileName"]
    size = msg["size"]

    logger.info(
        "[ServiceBusTrigger] documentId=%s fileName=%s size=%s",
        document_id,
        file_name,
        size,
    )

    if get_job(document_id) is None:
        raise ValueError(f"Document introuvable dans Cosmos : {document_id}")

    # ----- DÉBUT SIMULATION DLQ -----
    if "crash.pdf" in file_name.lower():
        logger.error("💥 Simulation de crash demandée pour crash.pdf !")
        raise Exception("Crash simulé pour tester la Dead Letter Queue")
    # ----- FIN SIMULATION DLQ -----

    pending_signalr: list[dict] = []

    if size == 0:
        error_message = "Fichier vide"
        patch_job(document_id, {
            "status": "ERROR",
            "errorMessage": error_message,
            "errorAt": _now_iso(),
        })
        _notify_job_update(pending_signalr, document_id, "ERROR", error_message)
        if pending_signalr:
            signalRMessages.set(json.dumps(pending_signalr))
        logger.warning("[ServiceBusTrigger] Fichier vide — statut ERROR")
        logger.info("=" * 60)
        return

    patch_job(document_id, {"status": "PROCESSING"})
    _notify_job_update(pending_signalr, document_id, "PROCESSING", "Traitement IA en cours")

    tags = generate_tags(file_name)

    patch_job(document_id, {
        "status": "PROCESSED",
        "tags": tags,
        "processedAt": _now_iso(),
    })
    _notify_job_update(pending_signalr, document_id, "PROCESSED", "Tagging terminé", tags)

    if pending_signalr:
        signalRMessages.set(json.dumps(pending_signalr))

    logger.info("[ServiceBusTrigger] Terminé — tags=%s", tags)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# 3. Service Bus DLQ Trigger (Alertes)
# ---------------------------------------------------------------------------

@app.service_bus_queue_trigger(
    arg_name="azservicebus",
    queue_name="document-processing/$DeadLetterQueue",
    connection="SERVICE_BUS_CONNECTION_STRING"
)
@app.generic_output_binding(
    arg_name="signalRMessages",
    type="signalR",
    hubName="documents",
    connectionStringSetting="SIGNALR_CONNECTION_STRING",
)
def dlq_alert_worker(azservicebus: func.ServiceBusMessage, signalRMessages: func.Out[str]) -> None:
    """
    Se déclenche quand un message finit dans la Dead Letter Queue.
    Passe le statut à ERROR et envoie une notification SignalR.
    """
    logger.warning("=" * 60)
    logger.warning("[DLQTrigger] Message reçu en Dead Letter Queue !")

    try:
        body = azservicebus.get_body().decode('utf-8')
        msg = json.loads(body)
    except Exception as exc:
        logger.error("[DLQTrigger] Impossible de lire le message : %s", exc)
        return
    
    document_id = msg.get("documentId")
    if not document_id:
        return
        
    error_message = "Message envoyé en DLQ après plusieurs échecs de traitement"
    
    try:
        patch_job(document_id, {
            "status": "ERROR",
            "errorMessage": error_message,
            "errorAt": _now_iso()
        })
    except Exception:
        pass
        
    pending_signalr: list[dict] = []
    _notify_job_update(pending_signalr, document_id, "ERROR", error_message)
    if pending_signalr:
        signalRMessages.set(json.dumps(pending_signalr))

    logger.warning("=" * 60)