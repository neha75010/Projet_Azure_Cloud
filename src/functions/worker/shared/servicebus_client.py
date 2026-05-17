"""
shared/servicebus_client.py
---------------------------
Envoie un message JSON sur une queue Azure Service Bus.

Variables attendues :
    SERVICE_BUS_CONNECTION_STRING : chaîne de connexion complète au namespace
    SERVICE_BUS_QUEUE_NAME        : nom de la queue (défaut: document-processing)
"""

import json
import logging
import os

from azure.servicebus import ServiceBusClient, ServiceBusMessage

logger = logging.getLogger(__name__)


def send_message(payload: dict) -> None:
    """
    Sérialise `payload` en JSON et l'envoie sur la queue Service Bus.

    Args:
        payload: dictionnaire quelconque — sera encodé en UTF-8.
    """
    conn_str = os.environ["SERVICE_BUS_CONNECTION_STRING"]
    queue_name = os.environ.get("SERVICE_BUS_QUEUE_NAME", "document-processing")

    body = json.dumps(payload, ensure_ascii=False)

    with ServiceBusClient.from_connection_string(conn_str) as sb_client:
        with sb_client.get_queue_sender(queue_name) as sender:
            msg = ServiceBusMessage(body)
            sender.send_messages(msg)

    logger.info(
        "Message envoyé sur la queue '%s' | documentId=%s",
        queue_name,
        payload.get("documentId", "?"),
    )
