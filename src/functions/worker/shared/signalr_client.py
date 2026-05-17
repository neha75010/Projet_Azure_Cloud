"""
Envoi immédiat vers Azure SignalR (REST API data-plane 2022-06-01).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

HUB_NAME = "documents"


def _parse_connection_string(conn_str: str) -> tuple[str, str]:
    parts: dict[str, str] = {}
    for segment in conn_str.split(";"):
        if "=" in segment:
            key, value = segment.split("=", 1)
            parts[key] = value
    endpoint = parts.get("Endpoint", "").rstrip("/")
    access_key = parts.get("AccessKey", "")
    if not endpoint or not access_key:
        raise ValueError("SIGNALR_CONNECTION_STRING invalide (Endpoint ou AccessKey manquant)")
    return endpoint, access_key


def _create_jwt(audience: str, access_key: str) -> str:
    exp = int(time.time()) + 3600
    header = (
        base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        .decode()
        .rstrip("=")
    )
    payload = (
        base64.urlsafe_b64encode(json.dumps({"aud": audience, "exp": exp}).encode())
        .decode()
        .rstrip("=")
    )
    unsigned = f"{header}.{payload}"
    signature = (
        base64.urlsafe_b64encode(
            hmac.new(access_key.encode(), unsigned.encode(), hashlib.sha256).digest()
        )
        .decode()
        .rstrip("=")
    )
    return f"{unsigned}.{signature}"


def build_job_update_event(
    document_id: str,
    status: str,
    message: str,
    tags: list[str] | None = None,
) -> dict:
    payload: dict = {
        "documentId": document_id,
        "status": status,
        "message": message,
    }
    if tags is not None:
        payload["tags"] = tags
    return {"target": "jobUpdate", "arguments": [payload]}


def push_job_update(
    document_id: str,
    status: str,
    message: str,
    tags: list[str] | None = None,
) -> bool:
    """
    Envoie un événement jobUpdate via REST. Retourne True si succès.
    """
    conn_str = os.environ.get("SIGNALR_CONNECTION_STRING", "")
    if not conn_str:
        logger.warning("[SignalR] SIGNALR_CONNECTION_STRING absent — notification ignorée")
        return False

    try:
        endpoint, access_key = _parse_connection_string(conn_str)
        # API v1 stable : POST /api/v1/hubs/{hub} (sans /:send)
        audience = f"{endpoint}/api/v1/hubs/{HUB_NAME}"
        url = audience
        token = _create_jwt(audience, access_key)

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=build_job_update_event(document_id, status, message, tags),
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.error("[SignalR] Échec envoi %s pour %s : %s", status, document_id, exc)
        return False
