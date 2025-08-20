from fastapi import APIRouter, HTTPException, Depends
from openai import AsyncOpenAI, APIError
from shared_utils.openai_client import get_openai_client
from shared_utils.chroma_client import get_chroma_client
import logging
import os
from metadata_service.models.metadata import MetadataRequest
from models.rag_config import QwenRAGConfig, QwenPromptTemplates, QwenRAGOptimizer, QueryType

router = APIRouter(prefix="/metadata")

logger = logging.getLogger(__name__)

# Initialize Qwen-2.5 RAG configuration
qwen_config = QwenRAGConfig()
prompt_templates = QwenPromptTemplates()
qwen_optimizer = QwenRAGOptimizer()

OPENAI_MODEL_NAME = qwen_config.model_name
TOP_K = int(os.getenv("MODEL_TOP_K"))

TEXTUAL_EMBEDDING_COLLECTION = "SentenceEmbeds"
MAX_CHUNK_IN_MEMORY = 10
SUMMARY_LENGTH = 500
EXECUTIVE_SUMMARY_LENGTH = 50

async def get_chunk(doc_id: str):
    chroma_client = await get_chroma_client()
    collection = await chroma_client.get_collection(TEXTUAL_EMBEDDING_COLLECTION)
    page = 0
    results = await collection.get(where={"doc_id": doc_id}, limit=MAX_CHUNK_IN_MEMORY, page= page)
    while results:
        page += 1
        for result in results:
            yield result
        results = await collection.get(where={"doc_id": doc_id}, limit=MAX_CHUNK_IN_MEMORY, page= page)


async def get_model_response(
        system_prompt: str,
        user_prompt: str,
        client: AsyncOpenAI = Depends(get_openai_client),
):
    # Prepare messages for Qwen-2.5
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user", 
            "content": user_prompt
        }
    ]

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
            **qwen_config.generation_params,
        )
        
    except APIError as e:
        logger.error(f"Unexpected error during chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during chat completion")

    if not response.choices:
        logger.error("No choices found in OpenAI response: %s", response)
        raise HTTPException(
            status_code=500,
            detail="No choices found in OpenAI response",
        )

    first_choice = response.choices[0]
    if not first_choice.message or first_choice.message.content is None:
        logger.error("Malformed choice in OpenAI response: %s", first_choice)
        raise HTTPException(
            status_code=500,
            detail="Malformed choice in OpenAI response",
        )
    
    processed_response = first_choice.message.content
    return processed_response


async def summarise_chunk(
    context: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    summary_len = SUMMARY_LENGTH if SUMMARY_LENGTH < len(context) else len(context)
    system_prompt = prompt_templates.get_system_prompt(QueryType.SUMMARIZATION)
    user_prompt = prompt_templates.format_user_prompt(f"Prepare a summary of {summary_len} words. Return only the summary.", context, QueryType.SUMMARIZATION)
    return await get_model_response(user_prompt, system_prompt, client)


async def prepare_summary(
    doc_id: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    summaries = []
    for chunk in get_chunk(doc_id):
        summaries.append(summarise_chunk(chunk, client))

    # naive assume that all chunks will fix in context
    summary_context = "\n".join(summaries)

    system_prompt = prompt_templates.get_system_prompt(QueryType.SUMMARIZATION)
    user_prompt = prompt_templates.format_user_prompt(f"Prepare a summary of {SUMMARY_LENGTH} words. Return only the summary.", summary_context, QueryType.SUMMARIZATION)
    return await get_model_response(user_prompt, system_prompt, client)

@router.get("/{doc_id}")
async def get_summary(
    doc_id: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    return await prepare_summary(doc_id, client)
    
