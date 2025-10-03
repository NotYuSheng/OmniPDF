from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import logging
from shared_utils.s3_utils import get_object_stream
from utils.session import validate_session_doc_pair

from botocore.exceptions import ClientError

router = APIRouter(prefix="/json_data", tags=["json_data"])
logger = logging.getLogger(__name__)


@router.get("/{doc_id}", response_class=StreamingResponse)
async def get_json(
    doc_id: str, json_name: str, _validated: bool = Depends(validate_session_doc_pair)
):
    key = f"{doc_id}/{json_name}.json"

    # Check if object exists
    try:
        file_stream = get_object_stream(key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="JSON file not found")
        raise HTTPException(status_code=500, detail="Failed to check JSON file")

    return StreamingResponse(file_stream, media_type="application/json")
