from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import logging
from shared_utils.s3_utils import download_fileobj
from utils.session import validate_session_doc_pair
from utils.proxy import stream_file

from botocore.exceptions import ClientError

router = APIRouter(prefix="/json_data", tags=["json_data"])
logger = logging.getLogger(__name__)


@router.get("/{doc_id}", status_code=200)
async def get_json(
    doc_id: str, json_name: str, _validated: bool = Depends(validate_session_doc_pair)
):
    key = f"{doc_id}/{json_name}.json"

    # Check if object exists
    try:
        file = download_fileobj(key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail="Failed to check document")

    return StreamingResponse(stream_file(file), media_type="application/json")
