import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from botocore.exceptions import ClientError

from models.images import ImageData, ImageResponse
from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_extraction_job, generate_external_image_url
from shared_utils.s3_utils import get_object_stream, list_folder
from shared_utils.redis import RedisDocumentFileList


router = APIRouter(prefix="/images", tags=["images"])
logger = logging.getLogger(__name__)
document_files = RedisDocumentFileList()


@router.get("/{doc_id}", response_model=ImageResponse)
async def get_pdf_images(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job=Depends(load_or_create_extraction_job),
):
    url_list = []

    prefix = f"{doc_id}/images/"
    keys = list_folder(prefix)

    for key in keys:
        image_name = key.rsplit("/", 1)[-1]
        url = generate_external_image_url(doc_id, image_name)
        url_list.append(ImageData(image_key=key, url=url))

    return ImageResponse(doc_id=doc_id, filename=f"{doc_id}.pdf", images=url_list)


@router.get("/{doc_id}/{img_name}", response_class=StreamingResponse)
async def get_pdf_image(
    doc_id: str,
    img_name: str,
    _validated: bool = Depends(validate_session_doc_pair),
):
    file_key = f"{doc_id}/images/{img_name}"

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
