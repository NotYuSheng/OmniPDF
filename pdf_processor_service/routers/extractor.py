import os
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends
from models.extractor import ExtractorResponse
from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_extraction_job, proxy_post
from shared_utils.s3_utils import generate_presigned_url

router = APIRouter(prefix="/extractor", tags=["extractor"])
logger = logging.getLogger(__name__)

EXTRACTION_URL = os.getenv("EXTRACTION_URL")
if not EXTRACTION_URL:
    raise ValueError("EXTRACTION_URL is not set")


@router.post("/{doc_id}", status_code=202)
async def submit_pdf_for_extraction(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
):
    """Submit a PDF for extraction processing."""
    presign_url = generate_presigned_url(f"{doc_id}/original.pdf")
    params = {"doc_id": doc_id, "download_url": presign_url}
    return await proxy_post(f"{EXTRACTION_URL}?{urlencode(params)}", body={})


@router.get("/{doc_id}", response_model=ExtractorResponse)
async def get_pdf_extraction(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job=Depends(load_or_create_extraction_job),
):
    """Get extraction results for a processed PDF."""
    # Extract result from job data
    job_data = job.get("data", {}).get("result", None)
    
    # Convert the job data to our response model
    extraction_response = ExtractorResponse(
        doc_id=doc_id,
        status=job.get("status", "unknown"),
        result=job_data if job_data else None
    )
    
    return extraction_response