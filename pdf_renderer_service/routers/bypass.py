from fastapi import APIRouter, File, UploadFile, HTTPException
import logging
from typing import Literal
from models.bypass import BypassResponse
import io


from shared_utils.s3_utils import (
    upload_fileobj,
    generate_presigned_url,
)

router = APIRouter(prefix="/bypass", tags=["bypass"])
logger = logging.getLogger(__name__)

@router.post("/{doc_id}")
async def dump_files(
    doc_id: str,
    json_name: Literal["original", "translated"],
    json_file: UploadFile = File(...),
    ):

    try:
        key = f"{doc_id}/{json_name}.json"
        file_content = await json_file.read()
        file_like = io.BytesIO(file_content)

        upload_fileobj(file_like, key, "application/json")
        logger.info(f"✅ Uploaded {key} to S3")

        return BypassResponse(
            doc_id=doc_id,
            filename=key,
            download_url=generate_presigned_url(key),
        )

    except Exception as e:
        logger.warning(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed due to an internal error.")
