from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
import os
import logging
import json
from utils.session import validate_session_doc_pair, get_session_id, validate_session_id, get_session_storage, SessionStorage
from utils.proxy import proxy_post
from models.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# Get chat service URL from environment
CHAT_SERVICE_URL = os.environ["CHAT_SERVICE_URL"]


async def proxy_chat_request(chat_request: ChatRequest, session_id: str) -> dict:
    """
    Proxy chat request to the chat service using the existing proxy_post utility
    """
    chat_request_dict = chat_request.model_dump()
    chat_request_dict['session_id'] = session_id
    try:
        # Use the existing proxy_post function
        response = await proxy_post(f"{CHAT_SERVICE_URL}/chat/", chat_request_dict)
        
        response_data = json.loads(response.body.decode('utf-8'))
        return response_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from chat service: {e}")
        raise HTTPException(status_code=500, detail="Invalid response from chat service") from e
    except Exception as e:
        # proxy_post already handles HTTPException raising, so we just re-raise
        raise


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
    validate_session_doc_pair(chat_request.doc_id, session_id, session_storage, _valid_session)
    try:
        logger.info(f"Processing chat request for session {session_id}")
        logger.info(f"Query: {chat_request.message}")
        if chat_request.doc_id:
            logger.info(f"Document ID: {chat_request.doc_id}")
        logger.info(f"Collection: {chat_request.collection_name}")
        
        # Proxy request to chat service
        chat_response = await proxy_chat_request(chat_request, session_id)
        
        logger.info(f"Chat response received with {len(chat_response.get('relevant_chunks', []))} relevant chunks")
        
        return ChatResponse(**chat_response)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat handler: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
