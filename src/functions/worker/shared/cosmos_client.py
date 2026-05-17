"""
shared/cosmos_client.py
-----------------------
Fournit un accès au conteneur Cosmos DB à partir des variables d'environnement
injectées par Azure Functions (ou local.settings.json en local).

Variables attendues :
    COSMOS_ENDPOINT   : https://<account>.documents.azure.com:443/
    COSMOS_KEY        : clé primaire Cosmos
    COSMOS_DATABASE   : nom de la base (défaut: db-doc)
    COSMOS_CONTAINER  : nom du conteneur (défaut: jobs)
"""

import logging
import os

from azure.cosmos import CosmosClient, ContainerProxy
from azure.cosmos.exceptions import CosmosHttpResponseError

logger = logging.getLogger(__name__)

JOB_PARTITION_KEY = "JOB"

_cosmos_client: CosmosClient | None = None
_container: ContainerProxy | None = None


def get_cosmos_container() -> ContainerProxy:
    """Retourne (et cache) le ContainerProxy Cosmos."""
    global _cosmos_client, _container
    if _container is not None:
        return _container

    endpoint = os.environ["COSMOS_ENDPOINT"]
    key = os.environ["COSMOS_KEY"]
    database = os.environ.get("COSMOS_DATABASE", "db-doc")
    container_name = os.environ.get("COSMOS_CONTAINER", "jobs")

    _cosmos_client = CosmosClient(url=endpoint, credential=key)
    db = _cosmos_client.get_database_client(database)
    _container = db.get_container_client(container_name)
    logger.info("Cosmos container prêt : %s / %s", database, container_name)
    return _container


def get_job(job_id: str) -> dict | None:
    """Retourne le job ou None si introuvable."""
    container = get_cosmos_container()
    try:
        return container.read_item(item=job_id, partition_key=JOB_PARTITION_KEY)
    except CosmosHttpResponseError as exc:
        if getattr(exc, "status_code", None) == 404:
            return None
        raise


def patch_job(job_id: str, fields: dict) -> dict:
    """
    Lit le document Cosmos, applique les champs, met updatedAt, et remplace.
    Retourne le document mis à jour.
    """
    from datetime import datetime, timezone

    container = get_cosmos_container()
    item = container.read_item(item=job_id, partition_key=JOB_PARTITION_KEY)
    item.update(fields)
    item["updatedAt"] = datetime.now(timezone.utc).isoformat()
    container.replace_item(item=item, body=item)
    return item
