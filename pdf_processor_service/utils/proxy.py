import os
import logging

from fastapi import HTTPException, Response
import httpx

from urllib.parse import urlencode
from shared_utils.s3_utils import load_job, generate_presigned_url

logger = logging.getLogger(__name__)

S3_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")  # MinIO-compatible
EXTRACTION_URL = os.getenv("EXTRACTION_URL")
if not EXTRACTION_URL:
    raise ValueError("EXTRACTION_URL is not set")


async def proxy_post(url: str, body: dict):
    async with httpx.AsyncClient() as client:
        try:
            req = await client.post(url, data=body)
            req.raise_for_status()  # Raise an exception for bad status codes
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error retrieving from {url}: {e}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Processor error: {e.response.text}",
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Request error retrieving from {url}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Could not connect to processor service: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error in HTTP request {url}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error") from e
        return Response(
            content=req.content, headers=req.headers, status_code=req.status_code
        )


async def load_or_create_job(doc_id: str) -> dict | Response:
    job = load_job(doc_id=doc_id, job_type="extraction")
    if not job:
        presign_url = generate_presigned_url(f"{doc_id}/original.pdf")
        param = {"doc_id": doc_id, "download_url": presign_url}
        return await proxy_post(f"{EXTRACTION_URL}?{urlencode(param)}", body=None)

    if job.get("status") == "processing":
        raise HTTPException(
            status_code=202,
            detail="The document is still being processed. Please try again later.",
        )

    return job


async def concat_text(doc_id: str) -> str:
    job = load_job(doc_id=doc_id, job_type="extraction")
    if job.get("status") == "processing":
        raise HTTPException(
            status_code=202,
            detail="The document is still being processed. Please try again later.",
        )
    
    texts = job.get("data", {}).get("result", {}).get("texts")
    text_list = [entry.get("text") or entry.get("orig") for entry in texts]
    return text_list.join("\n")