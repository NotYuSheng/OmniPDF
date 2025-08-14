import logging

from fastapi import APIRouter, Depends, Response

from models.images import ImageData, ImageResponse
from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_job
from shared_utils.s3_utils import generate_external_presigned_url, list_folder

router = APIRouter(prefix="/images", tags=["images"])
logger = logging.getLogger(__name__)



@router.get("/{doc_id}")
async def get_pdf_images(
        doc_id: str,    
        _validated: bool = Depends(validate_session_doc_pair),
    job_or_reposnse = Depends(load_or_create_job)
):
    if isinstance(job_or_reposnse, Response):
        return job_or_reposnse
    
    url_list = []

    prefix = f"{doc_id}/images/"
    keys = list_folder(prefix)
    
    for key in keys:
        url = generate_external_presigned_url(key)
        url_list.append(ImageData(image_key=key, url=url))

    return ImageResponse(doc_id=doc_id, filename=f"{doc_id}.pdf", images=url_list)
