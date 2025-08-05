from fastapi import APIRouter, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from openai import OpenAI, APIError
from shared_utils.openai_client import get_openai_client
import logging
import os
from models.chat import ChatRequest

router = APIRouter()
logger = logging.getLogger(__name__)

_OPENAI_MODEL_DEFAULT = "qwen2.5-0.5b-instruct"
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL", _OPENAI_MODEL_DEFAULT)


@router.post("/chat", status_code=201)
async def handle_chat(
    chat_request: ChatRequest,
    client: OpenAI = Depends(get_openai_client),
) -> dict[str, str]:
    """
    Handle incoming chat requests and return AI responses.
    """
    try:
        response = await run_in_threadpool(
            client.chat.completions.create,
            model=OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": chat_request.message,
                }
            ],
        )
    except APIError as e:
        logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    if not response.choices:
        logger.error("No choices found in OpenAI response: %s", response)
        raise HTTPException(
            status_code=500,
            detail="AI service returned no choices or an unexpected response format.",
        )

    first_choice = response.choices[0]
    if not first_choice.message or first_choice.message.content is None:
        logger.error("Malformed choice in OpenAI response: %s", first_choice)
        raise HTTPException(
            status_code=500,
            detail="AI service response choice is malformed or lacks content.",
        )

    return {"response": first_choice.message.content}
