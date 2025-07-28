from fastapi import APIRouter, Depends, HTTPException
import logging
from shared_utils.s3_utils import (
    generate_presigned_url,
    s3_client,
    S3_BUCKET,
)
from utils.session import validate_session_doc_pair

from botocore.exceptions import ClientError

router = APIRouter(prefix="/json_data", tags=["json_data"])
logger = logging.getLogger(__name__)

@router.get("/{doc_id}", status_code=200)
async def get_json(doc_id: str,
                  json_name: str,
                  valid_request: bool = Depends(validate_session_doc_pair)
                  ):
    if not valid_request:
        raise HTTPException(
            status_code=403,
            detail="User not authorized to access this document or invalid document ID",
        )

    key = f"{doc_id}/{json_name}.json"

        # Check if object exists
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail="Failed to check document")

    presigned_url = generate_presigned_url(key)
    return {"key": key, "url": presigned_url}