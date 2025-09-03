import os
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from typing import Optional
import itertools


from shared_utils.redis import RedisDocumentFileList

logger = logging.getLogger(__name__)

# Load from environment
S3_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")  # MinIO-compatible
S3_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
S3_BUCKET = os.getenv("MINIO_BUCKET", "omnifiles")
REGION_NAME = os.getenv("AWS_REGION", "ap-southeast-1")  # Optional; ignored by MinIO
EXTERNAL_ENDPOINT = os.getenv(
    "EXTERNAL_ENDPOINT", "http://localhost:8080/pdf_processor"
)

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


def delete_files(key_list: set[str]) -> bool:
    """
    Deletes a list of files from S3 using the given set.
    Returns True if all files was deleted, False if an error occured.
    """
    DELETE_OBJECT_LIMIT = 1000
    try:
        # Use itertools.islice for memory-efficient chunking
        for i in range(0, len(key_list), DELETE_OBJECT_LIMIT):
            chunk_keys = list(itertools.islice(key_list, i, i + DELETE_OBJECT_LIMIT))
            if not chunk_keys:
                break
            s3_client.delete_objects(
                Bucket=S3_BUCKET,
                Delete={"Objects": [{"Key": key} for key in chunk_keys], "Quiet": True},
            )
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
    try:
        keys = list_folder(folder_prefix)
        return delete_files(set(keys))
    except (BotoCoreError, ClientError) as e:
        logger.exception(f"Failed to delete file from S3: {e}")
        return False


