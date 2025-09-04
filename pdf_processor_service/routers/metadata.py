import os
import logging

from fastapi import APIRouter, Depends
from models.metadata import MetadataResponse
from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_sentence_embedder_job, load_or_create_metadata_job, proxy_post

router = APIRouter(prefix="/metadata", tags=["metadata"])
logger = logging.getLogger(__name__)

METADATA_URL = os.getenv("METADATA_URL")
if not METADATA_URL:
    raise ValueError("METADATA_URL is not set")


@router.post("/{doc_id}", status_code=202)
async def submit_pdf_for_metadata(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    _pre_req: dict = Depends(load_or_create_sentence_embedder_job)
):
    """Submit a PDF for metadata processing."""    
    # Then proceed with metadata processing
    return await proxy_post(f"{METADATA_URL}/metadata/{doc_id}", body={})


@router.get("/{doc_id}", response_model=MetadataResponse)
async def get_pdf_metadata(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job=Depends(load_or_create_metadata_job),
):
    """Get metadata for a processed PDF."""
    # Extract metadata from job data
    job_data = job.get("data", {}).get("result", None)
    
    # Convert the job data to our response model
    metadata_response = MetadataResponse(
        doc_id=doc_id,
        status=job.get("status", "unknown"),
        metadata=job_data if job_data else None
    )
    
    return metadata_response


