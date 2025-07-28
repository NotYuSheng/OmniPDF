import pymupdf
import logging
import io
import uuid
import time
import requests
import httpx
import fitz
from PyPDF2 import PdfReader, PdfWriter
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Body
from models.render import DocumentRendererResponse, AnnotationResponse

from shared_utils.s3_utils import (
    upload_fileobj,
    generate_presigned_url,
)

router = APIRouter(prefix="/render", tags=["render"])
logger = logging.getLogger(__name__)

@router.post("/{doc_id}")
async def pdf_render(
                doc_id: str,
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
        original_size = size_bytes / 1024 #in kb
    else:
        size_bytes = len(pdf_response.content)
        original_size = size_bytes / 1024 #in kb

    json_data = json_data.model_dump()
    doc = pymupdf.open(stream=pdf_response.content, filetype="pdf")
    trans_text_data = defaultdict(list)
    texts = json_data.get("docling", {}).get("texts", [])

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

    ### This section is supposed to handle table rendering but has been excluded due to autoscaling issues
    
    tables = json_data.get("docling", {}).get("tables", [])

    for table in tables:
        table_cells = table.get("data", {}).get("table_cells", [])
        page_no = table.get("prov", [])[0].get("page_no")

        for cell in table_cells:
            translated = cell.get("translated_text")
            bbox = cell.get("bbox")

            if page_no is not None and bbox:
                trans_text_data[page_no].append({
                    "translated_text": translated,
                    "bbox": bbox
                })

    data = dict(trans_text_data)

    for page in doc:
        logger.info(f"{page.number}\n") 
        blocks = page.get_text("blocks") 
        for block in blocks:
            rect = block[:4] 
            page.add_redact_annot(rect)

        page.apply_redactions()
        page.clean_contents()


        data_lst = data[page.number + 1]
        for trans_data in data_lst:
            trans_text = trans_data["translated_text"]
            bbox = trans_data['bbox']

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
                    raise e
            else:
                page.insert_htmlbox(coords, "Error")

    original_buffer = io.BytesIO()
    doc.subset_fonts()
    doc.save(original_buffer, garbage=4, deflate=True, clean=True)
    original_buffer.seek(0)

    compressed_buffer = io.BytesIO()

    reader = PdfReader(original_buffer)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    compressed_buffer = io.BytesIO()
    writer.write(compressed_buffer)
    compressed_buffer.seek(0)

    file_size = len(compressed_buffer.getvalue())

    rendered_size = file_size / 1024

    if original_size * 1.3 < rendered_size:
        logger.warning(f"File is bloated at {((rendered_size - original_size) / original_size) * 100:.2f}%")

    logger.info(f"Time to render document: {time.time() - start_time}")
    logger.info(f"File size: {original_size:.2f} => {file_size / 1024:.2f} KB")
    logger.info(f"File size: {original_size / 1024:.2f} => {file_size / (1024 * 1024):.2f} MB")

    doc_id = str(uuid.uuid4())
    key = f"{doc_id}/rendered.pdf"

    try:
        success = upload_fileobj(
            compressed_buffer, key, content_type="application/pdf"
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload file to S3")

        presigned_url = generate_presigned_url(key)

    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return(DocumentRendererResponse(doc_id=doc_id,
                                    filename=key,
                                    download_url=presigned_url,
                                    )
                                )