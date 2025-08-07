import pymupdf
import logging
import io
import uuid
import time
import httpx
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Body
from models.render import DocumentRendererResponse, AnnotationResponse
from botocore.exceptions import ClientError
from fastapi.concurrency import run_in_threadpool

from shared_utils.s3_utils import (
    upload_fileobj,
    generate_presigned_url,
)

router = APIRouter(prefix="/render", tags=["render"])
logger = logging.getLogger(__name__)

def redact_and_render(pdf_bytes: bytes, annotations: dict) -> bytes:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    trans_text_data = defaultdict(list)
    texts = annotations.get("docling", {}).get("texts", [])

    for text_item in texts:
        translated = text_item.get("translated_text", "")
        for prov in text_item.get("prov", []):
            page_no = prov.get("page_no")
            bbox = prov.get("bbox")

            bbox["b"] = doc[page_no-1].rect[3] - bbox["b"]
            bbox["t"] = doc[page_no-1].rect[3] - bbox["t"]

            if page_no is not None and bbox:
                trans_text_data[page_no].append({
                    "translated_text": translated,
                    "bbox": bbox
                })

    for page in doc:
        logger.info(f"{page.number}") 
        for cell in trans_text_data.get(page.number + 1, []):
            bbox = cell.get('bbox')
            rect_bbox = pymupdf.Rect(bbox["l"],
                                bbox["t"],
                                bbox["r"],
                                bbox["b"]
                            )
            page.add_redact_annot(rect_bbox)
        page.apply_redactions()
        page.clean_contents()

        data_lst = trans_text_data.get(page.number + 1, [])
        for trans_data in data_lst:
            trans_text = trans_data.get("translated_text")
            bbox = trans_data.get('bbox')
            if not trans_text or not bbox:
                continue

            coords = (bbox["l"], bbox["t"], bbox["r"], bbox["b"])

            logger.info(f"Text: {trans_text}")
            logger.info(f"Bbox: {coords}")

            if isinstance(trans_text, str):
                try:
                    page.insert_htmlbox(coords, trans_text)
                except Exception as e:
                    logger.error("Error inserting HTML box:")
                    logger.error(f"Text: {trans_text}")
                    logger.error(f"Original BBox: {bbox}")
                    logger.error(f"Converted Coords: {coords}")
                    logger.error(f"Page size: {page.rect}")
                    logger.exception(e)
                    raise
            else:
                page.insert_htmlbox(coords, "Error")

    buffer = io.BytesIO()
    doc.subset_fonts()
    doc.save(buffer, garbage=4, deflate=True, clean=True)
    buffer.seek(0)
    return buffer.getvalue()

def handle_file(buffer_bytes: bytes, key: str) -> str:
    """
    Sync helper to upload bytes to S3 and generate a presigned URL.
    Returns the presigned URL string.
    Raises ClientError or other on failure.
    """
    buf = io.BytesIO(buffer_bytes)
    # 1) upload
    success = upload_fileobj(buf, key, content_type="application/pdf")
    if not success:
        # mimic your existing HTTPException path
        raise RuntimeError("Failed to upload file to S3")
    # 2) generate presigned URL
    url = generate_presigned_url(key)
    return url
    
@router.post("/{doc_id}")
async def pdf_render(
                doc_url: str,
                json_data: AnnotationResponse = Body(...)
                ):

    start_time = time.time()
    async with httpx.AsyncClient() as client:
        pdf_response = await client.get(doc_url)
        pdf_response.raise_for_status()

    content_length = pdf_response.headers.get("Content-Length")
    if content_length:
        size_bytes = int(content_length)
    else:
        size_bytes = len(pdf_response.content)
    original_size = size_bytes / 1024
    json_data = json_data.model_dump()
    
    try:
        output_bytes = await run_in_threadpool(redact_and_render,
                                               pdf_response.content,
                                               json_data)
    except Exception as e:
        logger.error("Rendering failed", exc_info=True)
        raise HTTPException(500, f"PDF processing error {e}")

    buffer = io.BytesIO(output_bytes)
    file_size = len(buffer.getvalue())

    rendered_size = file_size / 1024

    if original_size * 1.3 < rendered_size:
        logger.warning(f"File is bloated at {((rendered_size - original_size) / original_size) * 100:.2f}%")

    logger.info(f"Time to render document: {time.time() - start_time}")
    logger.info(f"File size: {original_size:.2f} => {file_size / 1024:.2f} KB")
    logger.info(f"File size: {original_size / 1024:.2f} => {file_size / (1024 * 1024):.2f} MB")

    new_doc_id = str(uuid.uuid4())
    key = f"{new_doc_id}/rendered.pdf"

    try:
        presigned_url = await run_in_threadpool(
            handle_file,
            output_bytes,
            key
        )
        
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(f"S3 ClientError {code}", exc_info=True)
        raise HTTPException(502, f"S3 service error ({code})")
    except RuntimeError as e:
        # this covers your "upload returned False" path
        raise HTTPException(500, str(e))
    except Exception as e:
        logger.error("Unexpected upload error", exc_info=True)
        raise HTTPException(500, f"Internal server error {e}")
    
    return(DocumentRendererResponse(doc_id=new_doc_id,
                                    filename=key,
                                    download_url=presigned_url,
                                    )
                                )
