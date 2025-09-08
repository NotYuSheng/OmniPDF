import pymupdf
import logging
import io
import time
import httpx
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from models.render import DocumentRendererResponse, AnnotationResponse
from fastapi.concurrency import run_in_threadpool

from shared_utils.s3_utils import (
    upload_fileobj,
    generate_presigned_url,
)
from shared_utils.job_status import save_job, load_job, JobType, handle_job_status
from shared_utils.redis_utils import RedisDocumentFileList

router = APIRouter(prefix="/render", tags=["render"])
logger = logging.getLogger(__name__)

# Redis cache for document files
document_files = RedisDocumentFileList()


def redact_and_render(pdf_bytes: bytes, annotations: dict) -> bytes:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    trans_text_data = defaultdict(list)
    texts = annotations.get("docling", {}).get("texts", [])

    for text_item in texts:
        translated = text_item.get("translated_text", "")
        for prov in text_item.get("prov", []):
            page_no = prov.get("page_no")
            bbox = prov.get("bbox")

            bbox["b"] = doc[page_no - 1].rect[3] - bbox["b"]
            bbox["t"] = doc[page_no - 1].rect[3] - bbox["t"]

            if page_no is not None and bbox:
                trans_text_data[page_no].append(
                    {"translated_text": translated, "bbox": bbox}
                )

    for page in doc:
        logger.info(f"{page.number}")
        for cell in trans_text_data.get(page.number + 1, []):
            bbox = cell.get("bbox")
            rect_bbox = pymupdf.Rect(bbox["l"], bbox["t"], bbox["r"], bbox["b"])
            page.add_redact_annot(rect_bbox)
        page.apply_redactions()
        page.clean_contents()

        data_lst = trans_text_data.get(page.number + 1, [])
        for trans_data in data_lst:
            trans_text = trans_data.get("translated_text")
            bbox = trans_data.get("bbox")
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


async def process_render_job(doc_id: str, doc_url: str, json_data: dict):
    """
    Background task to process PDF rendering with translation overlays.
    """
    try:
        logger.info(f"Starting render job for doc_id: {doc_id}")
        start_time = time.time()
        
        # Fetch PDF from URL
        async with httpx.AsyncClient() as client:
            pdf_response = await client.get(doc_url)
            pdf_response.raise_for_status()
        
        content_length = pdf_response.headers.get("Content-Length")
        if content_length:
            size_bytes = int(content_length)
        else:
            size_bytes = len(pdf_response.content)
        original_size = size_bytes / 1024
        
        # Process the PDF with translation overlays
        output_bytes = await run_in_threadpool(
            redact_and_render, pdf_response.content, json_data
        )
        
        file_size = len(output_bytes)
        rendered_size = file_size / 1024
        
        if original_size * 1.3 < rendered_size:
            logger.warning(
                f"File is bloated at {((rendered_size - original_size) / original_size) * 100:.2f}%"
            )
        
        logger.info(f"Time to render document: {time.time() - start_time}")
        logger.info(f"File size: {original_size:.2f} => {file_size / 1024:.2f} KB")
        logger.info(
            f"File size: {original_size / 1024:.2f} => {file_size / (1024 * 1024):.2f} MB"
        )
        
        key = f"{doc_id}/rendered.pdf"
        
        # Upload to S3
        presigned_url = await run_in_threadpool(handle_file, output_bytes, key)
        
        # Add to document files cache
        document_files.add(doc_id, key)
        
        # Prepare result
        # result = DocumentRendererResponse(
        #     doc_id=doc_id,
        #     filename=key,
        #     download_url=presigned_url,
        # )
        result = {
            "doc_id": doc_id,
            "filename": key,
            "download_url": presigned_url,
        }
        
        # Save completed job
        save_job(
            doc_id=doc_id,
            job_data=result,
            status="completed",
            job_type=JobType.RENDERER
        )
        
        logger.info(f"Render job completed for doc_id: {doc_id}")
        
    except Exception as e:
        logger.error(f"Render job failed for doc_id: {doc_id} - {e}", exc_info=True)
        save_job(
            doc_id=doc_id,
            job_data={},
            status="failed",
            job_type=JobType.RENDERER
        )


@router.post("/{doc_id}", status_code=202)
async def pdf_render(
    doc_id: str, 
    background_tasks: BackgroundTasks,
    doc_url: str, 
    json_data: AnnotationResponse = Body(...)
):
    """Submit a PDF for rendering with translation overlays."""
    logger.info(f"Received render request for doc_id: {doc_id}")
    
    # Save initial job status
    save_job(
        doc_id=doc_id,
        job_data={},
        status="processing",
        job_type=JobType.RENDERER
    )
    
    # Start background processing
    background_tasks.add_task(
        process_render_job,
        doc_id,
        doc_url,
        json_data.model_dump()
    )
    
    return {"message": "Render job started", "doc_id": doc_id}


@router.get("/{doc_id}", response_model=DocumentRendererResponse)
async def get_render_result(doc_id: str):
    """Get the result of a completed render job."""
    job = load_job(doc_id=doc_id, job_type=JobType.RENDERER)
    
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    
    handle_job_status(job, JobType.RENDERER)
    
    job_data = job.get("data", {})
    
    # Extend expiry time for the rendered files
    rendered_doc_id = job_data.get("doc_id")
    if rendered_doc_id:
        _ = document_files[rendered_doc_id]
    
    return DocumentRendererResponse(**job_data)