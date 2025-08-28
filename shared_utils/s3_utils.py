import os
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from typing import Optional, Union
from pydantic import BaseModel

import json
from io import BytesIO

from shared_utils.redis import RedisDocumentFileList

logger = logging.getLogger(__name__)

# Load from environment
S3_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")  # MinIO-compatible
S3_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
S3_BUCKET = os.getenv("MINIO_BUCKET", "omnifiles")
REGION_NAME = os.getenv("AWS_REGION", "ap-southeast-1")  # Optional; ignored by MinIO
EXTERNAL_ENDPOINT = os.getenv("EXTERNAL_ENDPOINT", "http://localhost:8080/pdf_processor")

# Instantiate boto3 S3 client
s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=REGION_NAME,
)
document_files = RedisDocumentFileList()


def upload_fileobj(file_obj, key: str, content_type: str = "application/pdf") -> bool:
    """
    Uploads a file-like object to S3.
    """
    try:
        s3_client.upload_fileobj(
            Fileobj=file_obj,
            Bucket=S3_BUCKET,
            Key=key,
            ExtraArgs={"ContentType": content_type},
        )
        return True
    except (BotoCoreError, ClientError) as e:
        logger.exception(f"Failed to upload file to S3: {e}")
        return False


def get_object_stream(key: str):
    """
    Gets a streaming body for an object from S3.
    """
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        return response["Body"]
    except (BotoCoreError, ClientError) as e:
        logger.exception(f"Failed to get object stream from S3: {e}")
        raise


def generate_presigned_url(key: str, expiry_seconds: int = 300) -> Optional[str]:
    """
    Generates a presigned URL to download a file from S3.
    """
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expiry_seconds,
        )
    except (BotoCoreError, ClientError) as e:
        logger.exception(f"Failed to generate presigned URL: {e}")
        return None


def delete_file(key: str) -> bool:
    """
    Deletes a file from S3 using the given key.
    Returns True if the file existed and was deleted, False if it did not exist.
    """
    try:
        # Check if the file exists
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            logger.warning(f"File not found: {key}")
            return False
        else:
            logger.exception(f"Error checking if file exists: {e}")
            return False

    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
        logger.info(f"Deleted file with key: {key}")
        return True
    except (BotoCoreError, ClientError) as e:
        logger.exception(f"Failed to delete file from S3: {e}")
        return False


def list_folder(folder_prefix: str) -> list[str]:
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=folder_prefix)
    keys = [obj["Key"] for page in pages for obj in page.get("Contents", [])]
    return keys


def delete_folder(folder_prefix: str) -> bool:
    """
    Deletes a folder from S3 using the given key.
    Returns True if the folder was deleted, False if an error occured.
    """
    DELETE_OBJECT_LIMIT = 1000
    try:
        keys = list_folder(folder_prefix)
        chunked_keys = [
            keys[i : i + DELETE_OBJECT_LIMIT]
            for i in range(0, len(keys), DELETE_OBJECT_LIMIT)
        ]
        for chunk in chunked_keys:
            s3_client.delete_objects(
                Bucket=S3_BUCKET,
                Delete={"Objects": [{"Key": key} for key in chunk], "Quiet": True},
            )
        return True
    except (BotoCoreError, ClientError) as e:
        logger.exception(f"Failed to delete file from S3: {e}")
        return False


def get_job_s3_key(doc_id: str, job_type: str):
    return f"jobs/{job_type}/{doc_id}.json"


def save_job(
    doc_id: str, job_data: Union[dict, BaseModel], status: str, job_type: str
) -> bool:
    """
    Saves job data with metadata to S3 under a key based on the doc_id.
    """
    try:
        payload = (
            job_data.model_dump() if isinstance(job_data, BaseModel) else job_data or {}
        )
        wrapped = {
            "doc_id": doc_id,
            "status": status,
            "type": job_type,
            "data": payload,
        }
        file_obj = BytesIO(json.dumps(wrapped).encode("utf-8"))

        job_key = get_job_s3_key(doc_id, job_type)
        document_files.add(doc_id, job_key)
        return upload_fileobj(
            file_obj,
            key=job_key,
            content_type="application/json",
        )
    except Exception as e:
        logger.exception(f"Failed to save job for doc_id: {doc_id} - {e}")
        return False


def load_job(doc_id: str, job_type: str) -> Optional[dict]:
    """
    Loads job metadata and data from S3 given a doc_id.
    """
    try:
        job_key = get_job_s3_key(doc_id, job_type)
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=job_key)
        job = json.loads(response["Body"].read().decode("utf-8"))
        # Extend Expiry for document file list
        document_files[doc_id]
        return {
            "doc_id": doc_id,
            "status": job.get("status", "unknown"),
            "type": job.get("type", "unknown"),
            "data": job.get("data", None),
        }
    except (ClientError, BotoCoreError, json.JSONDecodeError) as e:
        logger.exception(f"Failed to load job for doc_id: {doc_id} - {e}")
        return None
