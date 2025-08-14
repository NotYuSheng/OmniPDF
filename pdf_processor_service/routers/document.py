from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import uuid
import logging
from shared_utils.s3_utils import (
    upload_fileobj,
    delete_file,
    get_object_stream,
)
from utils.session import (
    get_doc_list_append_function,
    get_doc_list_remove_function,
    validate_session_doc_pair,
)
from utils.proxy import generate_external_doc_url
from models.document import DocumentUploadResponse
from botocore.exceptions import ClientError

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...), append_doc=Depends(get_doc_list_append_function)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File extension must be .pdf")

    header = await file.read(4)
    if header != b"%PDF":
        raise HTTPException(
            status_code=400, detail="Uploaded file is not a valid PDF (header mismatch)"
        )
    await file.seek(0)

    doc_id = str(uuid.uuid4())
    key = f"{doc_id}/original.pdf"

    try:
        success = upload_fileobj(
            file.file, key, content_type=file.content_type or "application/pdf"
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload file to S3")

        url = generate_external_doc_url(doc_id)

    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    append_doc(doc_id)
    return DocumentUploadResponse(
        doc_id=doc_id, filename=key, download_url=url
    )


@router.get("/{doc_id}")
async def get_document(
    doc_id: str, _validated: bool = Depends(validate_session_doc_pair)
):
    key = f"{doc_id}/original.pdf"

    # Check if object exists
    try:
        file_stream = get_object_stream(key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail="Failed to check document")

    return StreamingResponse(file_stream, media_type="application/pdf")


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    remove_doc=Depends(get_doc_list_remove_function),
):
    key = f"{doc_id}/original.pdf"
    success = delete_file(key)
    if success:
        remove_doc(doc_id)
        logger.info(f"Successfully deleted document: {key}")
    else:
        logger.warning(f"Document not found or could not be deleted: {key}")
        raise HTTPException(status_code=404, detail="Document not found")
