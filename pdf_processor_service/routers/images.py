import logging

from fastapi import APIRouter, Depends, Response, HTTPException
from fastapi.responses import StreamingResponse
from botocore.exceptions import ClientError

from models.images import ImageData, ImageResponse
from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_job, generate_external_image_url

from shared_utils.s3_utils import get_object_stream, get_image_s3_key
from shared_utils.redis_utils import RedisDocumentFileList


router = APIRouter(prefix="/images", tags=["images"])
logger = logging.getLogger(__name__)
document_files = RedisDocumentFileList()


@router.get("/{doc_id}", response_model=ImageResponse)
async def get_pdf_images(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job_or_response=Depends(load_or_create_job),
):
    if isinstance(job_or_response, Response):
        return job_or_response
    job: dict = job_or_response
    images = job.get("data", {}).get("result", {}).get("pictures", [])

    image_list = []
    for img_data in images:
        image_name = img_data["key"]
        key = get_image_s3_key(doc_id, image_name)
        url = generate_external_image_url(doc_id, image_name)
        image_list.append(ImageData(image_key=key, url=url, caption=img_data["caption"]))

    return ImageResponse(doc_id=doc_id, filename=f"{doc_id}.pdf", images=image_list)


@router.get("/{doc_id}/{img_name}", response_class=StreamingResponse)
async def get_pdf_image(
    doc_id: str,
    img_name: str,
    _validated: bool = Depends(validate_session_doc_pair),
):
    file_key = get_image_s3_key(doc_id, img_name)

    # Check if object exists
    try:
        file_stream = get_object_stream(file_key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Image not found")
        raise HTTPException(status_code=500, detail="Failed to check Image")

    # To extend expiry time for the images
    _ = document_files[doc_id]

    return StreamingResponse(file_stream, media_type="image/png")
