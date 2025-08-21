from fastapi import APIRouter, File, UploadFile
import logging
from typing import Literal
from models.bypass import ImageBypassResponse
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
    image_id: Literal["original", "translated"],
    image_file: UploadFile = File(...),
    ):

    try:
        key = f"{doc_id}/images/{image_id}.png"
        file_content = await image_file.read()
        buffer = io.BytesIO(file_content)

        success = upload_fileobj(buffer, key, content_type="image/png")
        if not success:
            logger.warning(detail=f"Failed to upload picture {image_id} to S3")
            return {"error": "Error"}
        logger.info(f"Uploaded {key} to S3")

        return ImageBypassResponse(
            doc_id=doc_id,
            filename=key,
            download_url=generate_presigned_url(key),
        )

    except Exception as e:
        logger.warning(f"Upload failed: {e}")
        return {"error": "Error"}
    