from fastapi import APIRouter, Depends
import os
import logging
from utils.session import validate_session_doc_pair, get_session_id, validate_session_id, get_session_storage, SessionStorage
from utils.proxy import proxy_post
from models.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# Get chat service URL from environment
CHAT_SERVICE_URL = os.environ["CHAT_SERVICE_URL"]


@router.post("/", status_code=201, response_model=ChatResponse)
async def handle_chat(
    chat_request: ChatRequest,
    session_id: str = Depends(get_session_id),
    _valid_session: bool = Depends(validate_session_id),
    session_storage: SessionStorage = Depends(get_session_storage)
):
    """
    Handle chat requests with session validation and document access control.
    If doc_id is provided, validates that the user has access to that document.
    """
    for doc_id in chat_request.doc_ids:
        validate_session_doc_pair(doc_id, session_id, session_storage, _valid_session)

    logger.info(f"Processing chat request for session {session_id}")
    logger.info(f"Query: {chat_request.message}")
    logger.info(f"Document IDs: {chat_request.doc_ids}")
    logger.info(f"Collection: {chat_request.collection_name}")
    
    # Proxy request to chat service
    chat_request_dict = chat_request.model_dump()
    chat_request_dict['session_id'] = session_id
    return await proxy_post(f"{CHAT_SERVICE_URL}/chat/", chat_request_dict) 
        
