from datetime import datetime, timezone
from typing import Any

from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosHttpResponseError

JOB_PARTITION_KEY = "JOB"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def blob_path_for_job(job_id: str, file_name: str) -> str:
    return f"input/{job_id}/{file_name}"


def parse_blob_path(blob_name: str) -> tuple[str, str]:
    """Extrait documentId et fileName depuis input/{id}/{fileName}."""
    relative = blob_name.removeprefix("input/").lstrip("/")
    if "/" not in relative:
        raise ValueError(f"Blob path invalide: {blob_name}")
    document_id, file_name = relative.split("/", 1)
    if not document_id or not file_name:
        raise ValueError(f"Blob path invalide: {blob_name}")
    return document_id, file_name


def patch_job(container: ContainerProxy, job_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    item = container.read_item(item=job_id, partition_key=JOB_PARTITION_KEY)
    item.update(fields)
    item["updatedAt"] = now_iso()
    container.replace_item(item=item, body=item)
    return item


def get_job(container: ContainerProxy, job_id: str) -> dict[str, Any] | None:
    try:
        return container.read_item(item=job_id, partition_key=JOB_PARTITION_KEY)
    except CosmosHttpResponseError as e:
        if getattr(e, "status_code", None) == 404:
            return None
        raise
