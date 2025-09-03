import logging
import os
from typing import Literal
from json import JSONDecodeError

from fastapi import APIRouter, Depends, Request, Response

from utils.session import validate_session_doc_pair, get_session_id
from utils.proxy import concat_text, proxy_post, load_or_create_semantic_embedder_job, load_or_create_sentence_embedder_job

router = APIRouter(prefix="/embed", tags=["embed"])
logger = logging.getLogger(__name__)

EMBED_URL = os.getenv("EMBED_URL")
if not EMBED_URL:
    raise ValueError("EMBED_URL is not set")


@router.post("/{embed_type}/{doc_id}")
async def text_embed_proxy(
    embed_type: Literal["sentence", "semantic"],
    doc_id: str,
    request: Request,
    session_id: str = Depends(get_session_id),
    _validated: bool = Depends(validate_session_doc_pair),
    full_text: str = Depends(concat_text),
):
    # placeholder for pages_info, when implemented in the future
    pages_info = []
    # Get the config from the request body
    try:
        config = await request.json()
    except (ValueError, JSONDecodeError) as e:
        logger.error(f"Invalid JSON in request body: {e}")
        config = {}
    param = {
        "doc_id": doc_id,
        "session_id": session_id,
        "text": full_text,
        "config": config,
        "pages_info": pages_info,
    }
    return await proxy_post(f"{EMBED_URL}/{embed_type}/", body=param)


@router.get("/semantic/{doc_id}")
async def get_semantic_embedding_status(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job=Depends(load_or_create_semantic_embedder_job),
):
    """Get the status and results of semantic embedding processing"""
    # Extract result from job data
    job_data = job.get("data", {})
    
    return {
        "doc_id": doc_id,
        "status": job.get("status", "unknown"),
        "result": job_data if job.get("status") == "completed" else None
    }


@router.get("/sentence/{doc_id}")
async def get_sentence_embedding_status(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job=Depends(load_or_create_sentence_embedder_job),
):
    """Get the status and results of sentence embedding processing"""
    # Extract result from job data
    job_data = job.get("data", {})
    
    return {
        "doc_id": doc_id,
        "status": job.get("status", "unknown"),
        "result": job_data if job.get("status") == "completed" else None
    }
