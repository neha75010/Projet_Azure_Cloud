from fastapi import APIRouter, HTTPException
from azure.cosmos.exceptions import CosmosHttpResponseError
from .cosmos import get_cosmos_container
from .models import JobCreateRequest, JobCreateResponse, JobResponse, job_to_entity
from .blob_service import generate_upload_sas

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobCreateResponse, status_code=201)
def create_job(req: JobCreateRequest):
    container = get_cosmos_container()
    entity = job_to_entity(req)

    try:
        container.create_item(body=entity)
    except CosmosHttpResponseError as e:
        raise HTTPException(status_code=500, detail=f"Cosmos error: {getattr(e, 'message', str(e))}")

    upload_url = generate_upload_sas(entity["blobName"])

    return JobCreateResponse(
        jobId=entity["id"],
        status=entity["status"],
        createdAt=entity["createdAt"],
        uploadUrl=upload_url,
        blobName=entity["blobName"],
        category=entity["category"],
    )


@router.get("/{job_id}", response_model=JobResponse, summary="Récupérer un job par ID")
def get_job(job_id: str):
    container = get_cosmos_container()
    try:
        item = container.read_item(item=job_id, partition_key="JOB")
        return item
    except CosmosHttpResponseError as e:
        if getattr(e, "status_code", None) == 404:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=500, detail=f"Cosmos error: {getattr(e, 'message', str(e))}")
