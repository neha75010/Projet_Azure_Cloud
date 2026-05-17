from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uuid

from .job_utils import blob_path_for_job, now_iso

class JobCreateRequest(BaseModel):
    fileName: str = Field(..., min_length=1)
    contentType: str = Field(default="application/octet-stream")

class JobCreateResponse(BaseModel):
    jobId: str
    status: str
    createdAt: str
    uploadUrl: str
    blobName: str
    category: str = ""

class JobResponse(BaseModel):
    id: str
    pk: str
    status: str
    fileName: str
    contentType: str
    blobName: str
    category: str = ""
    tags: List[str] = Field(default_factory=list)
    size: Optional[int] = None
    createdAt: str
    updatedAt: str
    uploadedAt: Optional[str] = None
    processedAt: Optional[str] = None
    errorMessage: Optional[str] = None
    errorAt: Optional[str] = None
    resultSummary: Optional[str] = None

def job_to_entity(req: JobCreateRequest) -> Dict[str, Any]:
    job_id = str(uuid.uuid4())
    ts = now_iso()
    blob_name = blob_path_for_job(job_id, req.fileName)
    return {
        "id": job_id,
        "pk": "JOB",
        "status": "CREATED",
        "category": "",
        "fileName": req.fileName,
        "contentType": req.contentType,
        "blobName": blob_name,
        "tags": [],
        "size": None,
        "createdAt": ts,
        "updatedAt": ts,
        "uploadedAt": None,
        "processedAt": None,
        "errorMessage": None,
        "errorAt": None,
        "resultSummary": None,
    }
