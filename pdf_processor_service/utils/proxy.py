import os
import logging

from fastapi import HTTPException, Response
import httpx

from urllib.parse import urlencode
from shared_utils.s3_utils import load_job, generate_presigned_url

logger = logging.getLogger(__name__)

EXTERNAL_ENDPOINT = os.environ["EXTERNAL_ENDPOINT"]
METADATA_URL = os.environ["METADATA_URL"]
EXTRACTION_URL = os.environ["EXTRACTION_URL"]

if not EXTRACTION_URL:
    raise ValueError("EXTRACTION_URL is not set")


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
        raise HTTPException(
            status_code=400,
            detail=f"Bad request: {response.text}"
        )
    elif status_code == 401:
        logger.error(f"Unauthorized request to {url}")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized access to processor service"
        )
    elif status_code == 403:
        logger.error(f"Forbidden request to {url}")
        raise HTTPException(
            status_code=403,
            detail="Access forbidden to processor service"
        )
    elif status_code == 404:
        logger.error(f"Resource not found at {url}")
        raise HTTPException(
            status_code=404,
            detail="Resource not found in processor service"
        )
    elif status_code == 422:
        logger.error(f"Unprocessable entity at {url}: {response.text}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {response.text}"
        )
    elif status_code == 429:
        logger.error(f"Rate limit exceeded for {url}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for processor service"
        )
    elif 500 <= status_code < 600:
        logger.error(f"Server error from {url}: {status_code} - {response.text}")
        raise HTTPException(
            status_code=502,
            detail=f"Processor service error: {response.text}"
        )
    else:
        # Generic error for any other non-200 status codes
        logger.error(f"HTTP error {status_code} from {url}: {response.text}")
        raise HTTPException(
            status_code=status_code,
            detail=f"Processor error: {response.text}"
        )


def handle_job_status(job: dict, job_type: str = "document") -> None:
    """
    Handle job status validation and raise appropriate HTTPExceptions.
    
    Args:
        job: The job dictionary containing status information
        job_type: Type of job for error messaging (default: "document")
        
    Raises:
        HTTPException: With appropriate status code and error message
    """
    if not job:
        raise HTTPException(
            status_code=404, 
            detail=f"{job_type.capitalize()} not found or not processed yet"
        )
    
    if job.get("status") == "processing":
        raise HTTPException(
            status_code=202,
            detail=f"The {job_type} is still being processed. Please try again later.",
        )


async def proxy_post(url: str, body: dict):
    async with httpx.AsyncClient() as client:
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


async def load_or_create_job(doc_id: str) -> dict | Response:
    job = load_job(doc_id=doc_id, job_type="extraction")
    if not job:
        presign_url = generate_presigned_url(f"{doc_id}/original.pdf")
        param = {"doc_id": doc_id, "download_url": presign_url}
        return await proxy_post(f"{EXTRACTION_URL}?{urlencode(param)}", body=None)

    handle_job_status(job, "document")
    return job


async def load_or_create_metadata_job(doc_id: str) -> dict | Response:
    job = load_job(doc_id=doc_id, job_type="metadata")
    if not job:
        return await proxy_post(f"{METADATA_URL}/metadata/{doc_id}", body={})

    handle_job_status(job, "metadata")
    return job


async def concat_text(doc_id: str) -> str:
    job = load_job(doc_id=doc_id, job_type="extraction")
    handle_job_status(job, "document")
    
    texts = job.get("data", {}).get("result", {}).get("texts", [])
    text_list = [entry.get("text", "") or entry.get("orig", "") for entry in texts]
    return "\n".join(text_list)
  
  
def generate_external_image_url(doc_id: str, image_name: str):
    return f"{EXTERNAL_ENDPOINT}/images/{doc_id}/{image_name}"


def generate_external_doc_url(doc_id: str):
    return f"{EXTERNAL_ENDPOINT}/documents/{doc_id}"
