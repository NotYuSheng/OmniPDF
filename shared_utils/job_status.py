import logging
import json
from enum import StrEnum
from io import BytesIO
from typing import Optional

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException

from shared_utils.s3_utils import upload_fileobj, get_object_stream
from shared_utils.redis_utils import RedisDocumentFileList

logger = logging.getLogger(__name__)

document_files = RedisDocumentFileList()

class JobType(StrEnum):
    EXTRACTION = "extraction"
    SEMANTICEMBEDDER = "semantic_embedder"
    SENTENCEEMBEDDER = "sentence_embedder"
    METADATA = "metadata"
    TRANSLATION = "translation"
    RENDERER = "renderer"
    WORDCLOUD = "wordcloud"


def get_job_s3_key(doc_id: str, job_type: JobType) -> str:
    """
    Generate S3 key for job storage.
    
    Args:
        doc_id: Document identifier
        job_type: Type of job (e.g., 'extraction', 'metadata', 'embedding')
    
    Returns:
        S3 key string for the job
    """
    return f"jobs/{job_type}/{doc_id}.json"


def save_job(
    doc_id: str, job_data: dict, status: str, job_type: JobType, **metadata
) -> bool:
    """
    Saves job data with metadata to S3 under a key based on the doc_id.

    Args:
        doc_id: Document identifier
        job_data: Job data to save (dict or Pydantic model)
        status: Job status ('processing', 'completed', 'failed')
        job_type: Type of job (e.g., 'extraction', 'metadata', 'embedding')
        **metadata: Additional metadata to store (e.g., source_lang, target_lang)

    Returns:
        True if successful, False otherwise
    """
    wrapped = {
        "doc_id": doc_id,
        "status": status,
        "type": job_type,
        "data": job_data,
        **metadata  # Include any additional metadata
    }
    file_obj = BytesIO(json.dumps(wrapped).encode("utf-8"))

    job_key = get_job_s3_key(doc_id, job_type)
    document_files.add(doc_id, job_key)

    return upload_fileobj(file_obj, job_key, "application/json")


def load_job(doc_id: str, job_type: JobType) -> Optional[dict]:
    """
    Loads job metadata and data from S3 given a doc_id.
    
    Args:
        doc_id: Document identifier
        job_type: Type of job (e.g., 'extraction', 'metadata', 'embedding')
    
    Returns:
        Job dictionary with status and data, or None if not found
    """
    try:
        job_key = get_job_s3_key(doc_id, job_type)
        raw_job = get_object_stream(job_key)
        job = json.loads(raw_job.read().decode("utf-8"))
        # Extend Expiry for document file list
        document_files[doc_id]
        return {
            "doc_id": doc_id,
            "status": job.get("status", "unknown"),
            "type": job.get("type", "unknown"),
            "data": job.get("data", None),
        }
    except ClientError as e:
        # NoSuchKey is expected during polling before job is created
        if e.response.get("Error", {}).get("Code") == "NoSuchKey":
            logger.debug(f"Job not found yet for doc_id: {doc_id}, job_type: {job_type}")
        else:
            logger.exception(f"S3 client error loading job for doc_id: {doc_id} - {e}")
        return None
    except (BotoCoreError, json.JSONDecodeError) as e:
        logger.exception(f"Failed to load job for doc_id: {doc_id} - {e}")
        return None


def handle_job_status(job: dict, job_type: JobType, is_get_request: bool = True) -> None:
    """
    Handle job status validation and raise appropriate HTTPExceptions.

    Args:
        job: The job dictionary containing status information
        job_type: Type of job for error messaging
        is_get_request: If True (default), allows processing status to pass through (GET polling).
                       If False, raises 202 for processing status (POST submission).

    Raises:
        HTTPException: With appropriate status code and error message
    """
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"{job_type.capitalize()} not found or not processed yet",
        )

    if job.get("status") == "processing":
        if is_get_request:
            # For GET requests, processing status is normal - don't raise exception
            # The endpoint returns the job with status="processing" in response body
            return
        else:
            # For POST requests that trigger async processing, return 202 Accepted
            raise_processing_error(job_type)

    if job.get("status") == "failed":
        # Failed jobs should return 500 Internal Server Error for both GET and POST
        raise HTTPException(
            status_code=500,
            detail=f"The {job_type} has failed. Please retry the job."
        )


def raise_processing_error(process_name: str) -> None:
    """
    Raise a 202 HTTP error indicating that a process is still running.

    Args:
        process_name: Name of the process that is still running

    Raises:
        HTTPException: With status code 202 and appropriate message
    """
    raise HTTPException(
        status_code=202,
        detail=f"The {process_name} is still processing. Please try again later.",
    )