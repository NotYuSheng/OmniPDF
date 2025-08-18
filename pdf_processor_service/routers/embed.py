import logging
import os

from fastapi import APIRouter, Depends

from utils.session import validate_session_doc_pair, get_session_id
from utils.proxy import concat_text, proxy_post

router = APIRouter(prefix="/embed", tags=["embed"])
logger = logging.getLogger(__name__)

EMBED_URL = os.getenv("EMBED_URL")
if not EMBED_URL:
    raise ValueError("EMBED_URL is not set")


@router.get("/{embed_type}/{doc_id}")
async def text_embed_proxy(
    embed_type: str,
    doc_id: str,
    session_id: str = Depends(get_session_id),
    _validated: bool = Depends(validate_session_doc_pair),
    full_text: str = Depends(concat_text)
):
    
    param = {"doc_id": doc_id, "session_id": session_id, "text": full_text, "config": {}, "pages_info": []}
    return await proxy_post(f"{EMBED_URL}/{embed_type}/", body=param)
