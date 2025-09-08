import os
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from models.renderer import RendererResponse
from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_translation_job, load_or_create_render_job, proxy_post
from shared_utils.s3_utils import generate_presigned_url, get_object_stream
from shared_utils.redis_utils import RedisDocumentFileList
from botocore.exceptions import ClientError
from urllib.parse import urlencode

router = APIRouter(prefix="/renderer", tags=["renderer"])
logger = logging.getLogger(__name__)
document_files = RedisDocumentFileList()

RENDERER_URL = os.getenv("RENDERER_URL")
if not RENDERER_URL:
    raise ValueError("RENDERER_URL is not set")



@router.post("/{doc_id}", status_code=202)
async def submit_pdf_for_rendering(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    translation_job: dict = Depends(load_or_create_translation_job)
):
    """Submit a PDF for rendering with translation overlays."""
    # Get the translation result to send to renderer service
    translation_result = translation_job.get("data", {})
    
    # Generate the document URL for the renderer
    doc_url = generate_presigned_url(f"{doc_id}/original.pdf")
    logger.info(doc_url)
    
    # Prepare request body for renderer service
    render_request = {
        "doc_id": doc_id,
        "docling": translation_result
    }

    # Use centralized proxy_post function
    return await proxy_post(f"{RENDERER_URL}/render/{doc_id}?{urlencode({"doc_url":doc_url})}", body=render_request)


@router.get("/{doc_id}", response_model=RendererResponse)
async def get_pdf_rendering(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job: str = Depends(load_or_create_render_job),
):
    """Get rendering results for a processed PDF."""
    # Extract result from job data
    job_data = job.get("data", {})
    
    # Convert the job data to our response model
    render_response = RendererResponse(
        doc_id=doc_id,
        status=job.get("status", "unknown"),
        result=job_data
    )
    
    return render_response

@router.get("/{doc_id}/render.pdf", response_model=RendererResponse)
async def get_pdf_rendered_file(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job: str = Depends(load_or_create_render_job),
):
    """Get rendering results for a processed PDF."""
    file_key = f"{doc_id}/render.pdf"
    job.get("data", {}).get("filename", "")
    # Check if wordcloud image exists in S3
    try:
        file_stream = get_object_stream(file_key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Rendered pdf not found")
        else:
            raise HTTPException(status_code=500, detail="Failed to retrieve Rendered PDF")
    
    # Extend expiry time for the wordcloud files
    document_files[doc_id]
    
    return StreamingResponse(file_stream, media_type="application/pdf")
