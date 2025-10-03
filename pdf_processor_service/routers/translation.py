import os
import logging

from fastapi import APIRouter, Depends
from models.translation import TranslationRequest, TranslationResponse
from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_extraction_job, load_or_create_translation_job, proxy_post

router = APIRouter(prefix="/translation", tags=["translation"])
logger = logging.getLogger(__name__)

TRANSLATION_URL = os.getenv("TRANSLATION_URL")
if not TRANSLATION_URL:
    raise ValueError("TRANSLATION_URL is not set")


@router.post("/{doc_id}", status_code=202)
async def submit_pdf_for_translation(
    doc_id: str,
    request: TranslationRequest,
    _validated: bool = Depends(validate_session_doc_pair),
):
    """Submit a PDF for translation processing."""
    # Ensure extraction is complete first (will raise 202 if still processing)
    job = await load_or_create_extraction_job(doc_id, is_get_request=False)

    # Get the extraction result to send to translation service
    extraction_result = job.get("data", {}).get("result", {})
    
    # Prepare request body for translation service
    translation_request = {
        "doc_id": doc_id,
        "docling": extraction_result,
        "source_lang": request.source_lang,
        "target_lang": request.target_lang,
    }

    return await proxy_post(f"{TRANSLATION_URL}/translation/", body=translation_request)


@router.get("/{doc_id}", response_model=TranslationResponse)
async def get_pdf_translation(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job: dict = Depends(load_or_create_translation_job),
):
    """Get translation results for a processed PDF."""
    # Extract result from job data
    job_data = job.get("data", {})

    # Extract source and target languages from job metadata
    source_lang = job.get("source_lang")
    target_lang = job.get("target_lang")

    # Convert the job data to our response model
    translation_response = TranslationResponse(
        doc_id=doc_id,
        status=job.get("status", "unknown"),
        source_lang=source_lang,
        target_lang=target_lang,
        result=job_data if job.get("status") == "completed" and job_data else None
    )

    return translation_response

