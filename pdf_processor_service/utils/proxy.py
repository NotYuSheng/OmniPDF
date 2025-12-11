import os
import logging

from fastapi import HTTPException, Response, Depends
import httpx

from urllib.parse import urlencode
from utils.session import get_session_id
from shared_utils.s3_utils import generate_presigned_url
from shared_utils.job_status import load_job, handle_job_status, raise_processing_error, JobType

logger = logging.getLogger(__name__)

EXTERNAL_ENDPOINT = os.environ["EXTERNAL_ENDPOINT"]
EXTRACTION_URL = os.environ["EXTRACTION_URL"]
TRANSLATION_URL = os.environ["TRANSLATION_URL"]
RENDERER_URL = os.environ["RENDERER_URL"]


def handle_status_error(response: httpx.Response, url: str) -> None:
    """
    Handle HTTP status errors for requests that don't return status code 200.

    Args:
        response: The HTTP response object
        url: The URL that was requested

    Raises:
        HTTPException: With appropriate status code and error message
    """
    status_code = response.status_code

    # Handle specific status codes with meaningful messages
    if 200 <= status_code < 300:
        # No error, successful response
        return
    elif status_code == 400:
        logger.error(f"Bad request to {url}: {response.text}")
        raise HTTPException(status_code=400, detail=f"Bad request: {response.text}")
    elif status_code == 401:
        logger.error(f"Unauthorized request to {url}")
        raise HTTPException(
            status_code=401, detail="Unauthorized access to processor service"
        )
    elif status_code == 403:
        logger.error(f"Forbidden request to {url}")
        raise HTTPException(
            status_code=403, detail="Access forbidden to processor service"
        )
    elif status_code == 404:
        logger.error(f"Resource not found at {url}")
        raise HTTPException(
            status_code=404, detail="Resource not found in processor service"
        )
    elif status_code == 422:
        logger.error(f"Unprocessable entity at {url}: {response.text}")
        raise HTTPException(
            status_code=422, detail=f"Validation error: {response.text}"
        )
    elif status_code == 429:
        logger.error(f"Rate limit exceeded for {url}")
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded for processor service"
        )
    elif 500 <= status_code < 600:
        logger.error(f"Server error from {url}: {status_code} - {response.text}")
        raise HTTPException(
            status_code=502, detail=f"Processor service error: {response.text}"
        )
    else:
        # Generic error for any other non-200 status codes
        logger.error(f"HTTP error {status_code} from {url}: {response.text}")
        raise HTTPException(
            status_code=status_code, detail=f"Processor error: {response.text}"
        )


async def proxy_post(url: str, body: dict):
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            req = await client.post(url, json=body)
            # Check if status code is not 200 and handle the error
            if req.status_code != 200:
                handle_status_error(req, url)

        except httpx.RequestError as e:
            logger.error(f"Request error retrieving from {url}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Could not connect to processor service: {e}"
            ) from e
        return Response(
            content=req.content, headers=req.headers, status_code=req.status_code
        )


async def load_or_create_extraction_job(doc_id: str, is_get_request: bool = True) -> dict | Response:
    job_type = JobType.EXTRACTION
    job = load_job(doc_id=doc_id, job_type=job_type)
    if not job:
        presign_url = generate_presigned_url(f"{doc_id}/original.pdf")
        param = {"doc_id": doc_id, "download_url": presign_url}
        response = await proxy_post(f"{EXTRACTION_URL}?{urlencode(param)}", body=None)
        if response.status_code == 202:
            raise_processing_error(job_type)
        else:
            logger.error(f"Post to {job_type} returned HTTP code {response.status_code}")
            raise HTTPException(status_code=500, detail=f"{job_type} has returned an unexpected response.")

    handle_job_status(job, job_type, is_get_request=is_get_request)
    return job


async def load_or_create_translation_job(
    doc_id: str,
    source_lang: str = "",
    target_lang: str = "",
    is_get_request: bool = True
) -> dict | Response:
    """Load existing translation job or create a new one if it doesn't exist.

    Note: Translation jobs should only be created via explicit POST requests with
    source_lang and target_lang. GET requests will raise 404 if job doesn't exist.
    """
    job_type = JobType.TRANSLATION
    job = load_job(doc_id=doc_id, job_type=job_type)
    if not job:
        # Translation requires explicit source/target languages
        # Don't auto-create on GET requests or with empty languages
        if is_get_request:
            raise HTTPException(
                status_code=404,
                detail="Translation not found. Please submit a translation request first."
            )

        if not source_lang or not target_lang:
            raise HTTPException(
                status_code=400,
                detail="source_lang and target_lang are required to create a translation job."
            )

        # Ensure extraction is complete first
        extraction_job = await load_or_create_extraction_job(doc_id, is_get_request=False)

        # Get the extraction result to send to translation service
        extraction_result = extraction_job.get("data", {}).get("result", {})

        # Prepare request body for translation service
        translation_request = {
            "doc_id": doc_id,
            "docling": extraction_result,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }

        response = await proxy_post(f"{TRANSLATION_URL}/translation/", body=translation_request)
        if response.status_code == 202:
            raise_processing_error(job_type)
        else:
            logger.error(f"Post to {job_type} returned HTTP code {response.status_code}")
            raise HTTPException(status_code=500, detail=f"{job_type} has returned an unexpected response.")

    handle_job_status(job, job_type, is_get_request=is_get_request)
    return job


async def load_or_create_render_job(
    doc_id: str,
    is_get_request: bool = True
) -> dict | Response:
    """Load existing render job or create a new one if it doesn't exist"""
    job_type = JobType.RENDERER

    # First check if we have a local job for this render request
    job = load_job(doc_id=doc_id, job_type=job_type)
    if not job:
        # Ensure translation is complete first
        translation_job = await load_or_create_translation_job(doc_id, is_get_request=False)

        # Get the translation result to send to renderer service
        translation_result = translation_job.get("data", {})

        # Generate the document URL for the renderer
        doc_url = generate_presigned_url(f"{doc_id}/original.pdf")

        # Prepare request body for renderer service
        render_request = {
            "doc_id": doc_id,
            "docling": translation_result
        }

        # Make request with doc_url as query parameter
        response = await proxy_post(f"{RENDERER_URL}/render/{doc_id}?{urlencode({'doc_url': doc_url})}", body=render_request)
        if response.status_code == 202:
            raise_processing_error(job_type)
        else:
            logger.error(f"Post to {job_type} returned HTTP code {response.status_code}")
            raise HTTPException(status_code=500, detail=f"{job_type} has returned an unexpected response.")

    handle_job_status(job, job_type, is_get_request=is_get_request)
    return job


async def concat_text(doc_id: str) -> str:
    job = await load_or_create_extraction_job(doc_id, is_get_request=False)

    texts = job.get("data", {}).get("result", {}).get("texts", [])
    text_list = [entry.get("text", "") or entry.get("orig", "") for entry in texts]
    return "\n".join(text_list)


def generate_external_image_url(doc_id: str, image_name: str):
    return f"{EXTERNAL_ENDPOINT}/images/{doc_id}/{image_name}"


def generate_external_doc_url(doc_id: str):
    return f"{EXTERNAL_ENDPOINT}/documents/{doc_id}"
