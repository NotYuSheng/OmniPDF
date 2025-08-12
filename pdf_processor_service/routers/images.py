from datetime import timedelta
import logging

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse

from models.images import ImageData, ImageResponse
from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_job, generate_external_image_url
from shared_utils.s3_utils import s3_client, S3_BUCKET, download_fileobj
from shared_utils.redis import RedisSetWithFlagExpiry

router = APIRouter(tags=["images"])
logger = logging.getLogger(__name__)
redis_image_sets = RedisSetWithFlagExpiry(prefix="ImageFiles", flag_prefix="S3Key", default_expiry=timedelta(hours=1))


@router.get("/images/{doc_id}")
async def get_pdf_images(
        doc_id: str,
        _validated: bool = Depends(validate_session_doc_pair),
    job_or_reposnse = Depends(load_or_create_job)
):
    if isinstance(job_or_reposnse, Response):
        return job_or_reposnse
    
    url_list = []

    prefix = f"{doc_id}/images/"
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
    keys = [obj['Key'] for page in pages for obj in page.get('Contents', [])]
    
    for key in keys:
        image_name = key.rsplit("/", 1)[-1]
        url = generate_external_image_url(doc_id, image_name)
        url_list.append(ImageData(image_key=key, url=url))

    return ImageResponse(doc_id=doc_id, filename=f"{doc_id}.pdf", images=url_list)

@router.get("/image/{doc_id}/{img_name}")
async def get_pdf_image(
        doc_id: str,
        img_name: str,
        _validated: bool = Depends(validate_session_doc_pair),
):
    file_key = f"{doc_id}/images/{img_name}"
    file = download_fileobj(file_key)

    # To extend expiry time for the images
    _ = redis_image_sets[doc_id]

    def stream_file():
        with file:
            yield from file
    return StreamingResponse(stream_file(), media_type="image/png")