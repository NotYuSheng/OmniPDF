import os
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from botocore.exceptions import ClientError

from models.metadata import WordcloudResponse
from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_job, handle_status_error
from shared_utils.s3_utils import get_object_stream
from shared_utils.redis import RedisDocumentFileList
import httpx

router = APIRouter(prefix="/wordcloud", tags=["wordcloud"])
logger = logging.getLogger(__name__)

# Redis cache for wordcloud files
document_files = RedisDocumentFileList()

METADATA_URL = os.getenv("METADATA_URL")
if not METADATA_URL:
    raise ValueError("METADATA_URL is not set")


@router.get("/{doc_id}", response_model=WordcloudResponse)
async def get_pdf_wordcloud(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job: dict = Depends(load_or_create_job)
):
    """Get wordcloud data for a processed PDF."""
    # Make request to metadata service wordcloud endpoint
    async with httpx.AsyncClient() as client:
        try:
            wordcloud_url = f"{METADATA_URL}/wordcloud/{doc_id}"
            response = await client.get(wordcloud_url)
            
            if response.status_code != 200:
                handle_status_error(response, wordcloud_url)
                
        except httpx.RequestError as e:
            logger.error(f"Request error retrieving wordcloud from {wordcloud_url}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Could not connect to metadata service: {e}"
            ) from e
        except HTTPException:
            # Re-raise HTTPExceptions from handle_status_error
            raise
        except Exception as e:
            logger.error(f"Unexpected error in wordcloud request: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error") from e
    
    # Parse and return the response
    wordcloud_data = response.json()
    return WordcloudResponse(
        doc_id=wordcloud_data["doc_id"],
        top_words=wordcloud_data["top_words"]
    )


@router.get("/{doc_id}/wordcloud.png", response_class=StreamingResponse)
async def get_pdf_wordcloud_image(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
):
    """Get the wordcloud image for a processed PDF."""
    file_key = f"{doc_id}/wordcloud.png"
    
    # Check if wordcloud image exists in S3
    try:
        file_stream = get_object_stream(file_key)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            # If image doesn't exist, trigger wordcloud generation first
            try:
                await get_pdf_wordcloud(doc_id, _validated=True)
                # Try to get the file again after generation
                file_stream = get_object_stream(file_key)
            except ClientError:
                raise HTTPException(status_code=404, detail="Wordcloud image not found")
        else:
            raise HTTPException(status_code=500, detail="Failed to retrieve wordcloud image")
    
    # Extend expiry time for the wordcloud files
    _ = document_files[doc_id]
    
    return StreamingResponse(file_stream, media_type="image/png")