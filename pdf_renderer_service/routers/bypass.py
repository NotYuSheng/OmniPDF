import logging
from typing import Literal
from models.bypass import BypassResponse
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.concurrency import run_in_threadpool
from io import BytesIO

from shared_utils.s3_utils import (
    upload_fileobj,
    generate_presigned_url,
)

router = APIRouter(prefix="/bypass", tags=["bypass"])
logger = logging.getLogger(__name__)


def s3_upload(file_bytes: bytes, key: str) -> str:
    """
    Sync helper: upload bytes to S3 and return a presigned URL.
    Raises exceptions on failure.
    """
    bio = BytesIO(file_bytes)
    success = upload_fileobj(bio, key, content_type="application/json")
    if not success:
        raise RuntimeError(f"S3 upload returned False for key {key}")
    return generate_presigned_url(key)


@router.post("/{doc_id}")
async def dump_files(
    doc_id: str,
    json_name: Literal["original", "translated"],
    json_file: UploadFile = File(...),
):
    key = f"{doc_id}/{json_name}.json"

    # ensure we read the file from the start
    await json_file.seek(0)
    file_bytes = await json_file.read()

    try:
        # offload both upload + URL generation to threadpool
        presigned_url = await run_in_threadpool(s3_upload, file_bytes, key)

        logger.info(f"✅ Uploaded {key} to S3")

        return BypassResponse(
            doc_id=doc_id,
            filename=key,
            download_url=presigned_url,
        )

    except Exception as e:
        logger.warning(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Upload failed due to an internal error."
        )
