from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
import uuid
import logging
from shared_utils.s3_utils import (
    upload_fileobj,
    generate_presigned_url,
    delete_file,
    s3_client,
    S3_BUCKET,
)
from utils.session import (
    get_doc_list_append_function,
    get_doc_list_remove_function,
    validate_session_doc_pair,
)
from utils.proxy import get_external_minio_uri
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

        presigned_url = generate_presigned_url(key)
        if not presigned_url:
            raise HTTPException(
                status_code=500, detail="Failed to generate presigned URL"
            )

    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    append_doc(doc_id)
    presigned_url = get_external_minio_uri(presigned_url)

    return DocumentUploadResponse(
        doc_id=doc_id, filename=key, download_url=presigned_url
    )


@router.get("/{doc_id}", response_model=DocumentUploadResponse)
async def get_document(
    doc_id: str, valid_request: bool = Depends(validate_session_doc_pair)
):
    key = f"{doc_id}/original.pdf"

    # Check if object exists
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail="Failed to check document")

    presigned_url = generate_presigned_url(key)
    presigned_url = get_external_minio_uri(presigned_url)
    return DocumentUploadResponse(
        doc_id=doc_id, filename=key, download_url=presigned_url
    )


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    valid_request: bool = Depends(validate_session_doc_pair),
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