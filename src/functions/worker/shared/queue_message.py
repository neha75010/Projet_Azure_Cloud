import json
from typing import Any


class InvalidQueueMessageError(ValueError):
    """Message Service Bus mal formé — doit finir en DLQ après retries."""


def parse_queue_message(body: str) -> dict[str, Any]:
    try:
        msg = json.loads(body)
    except json.JSONDecodeError as exc:
        raise InvalidQueueMessageError("Message JSON invalide") from exc

    if not isinstance(msg, dict):
        raise InvalidQueueMessageError("Le message doit être un objet JSON")

    document_id = msg.get("documentId")
    file_name = msg.get("fileName")
    if not document_id or not file_name:
        raise InvalidQueueMessageError("documentId ou fileName manquant")

    if "size" not in msg:
        raise InvalidQueueMessageError("size manquant")

    try:
        msg["size"] = int(msg["size"])
    except (TypeError, ValueError) as exc:
        raise InvalidQueueMessageError("size doit être un entier") from exc

    return msg
