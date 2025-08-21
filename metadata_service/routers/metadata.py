from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from openai import AsyncOpenAI, APIError
from shared_utils.openai_client import get_openai_client
from shared_utils.chroma_client import get_chroma_client
from shared_utils.redis import RedisStringStorage
from shared_utils.s3_utils import save_job, load_job
import logging
import os
from models.rag_config import (
    QwenRAGConfig,
    QwenPromptTemplates,
    QwenRAGOptimizer,
    QueryType,
)

router = APIRouter(prefix="/metadata")

logger = logging.getLogger(__name__)

# Initialize Qwen-2.5 RAG configuration
qwen_config = QwenRAGConfig()
prompt_templates = QwenPromptTemplates()
qwen_optimizer = QwenRAGOptimizer()

OPENAI_MODEL_NAME = qwen_config.model_name
TOP_K = int(os.getenv("MODEL_TOP_K"))

FILENAME_REDIS_PREFIX = "Filename"
TEXTUAL_EMBEDDING_COLLECTION = "SentenceEmbeds"
MAX_CHUNK_IN_MEMORY = 10
SUMMARY_LENGTH = 500
SHORT_DSECRIPTION_LENGTH = 20


async def get_chunk(doc_id: str):
    chroma_client = await get_chroma_client()
    collection = await chroma_client.get_collection(TEXTUAL_EMBEDDING_COLLECTION)
    offset = 0
    results = await collection.get(
        where={"doc_id": doc_id}, limit=MAX_CHUNK_IN_MEMORY, offset=offset
    )
    logger.info(results)
    while results["documents"]:
        offset += MAX_CHUNK_IN_MEMORY
        for result in results["documents"]:
            yield result
        results = await collection.get(
            where={"doc_id": doc_id}, limit=MAX_CHUNK_IN_MEMORY, offset=offset
        )


async def get_model_response(
    system_prompt: str,
    user_prompt: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    # Prepare messages for Qwen-2.5
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
            **qwen_config.generation_params,
        )

    except APIError as e:
        logger.error(f"Unexpected error during chat completion: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Unexpected error during chat completion"
        )

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


@router.get("/summary/{doc_id}")
async def get_summary(
    doc_id: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    system_prompt = prompt_templates.get_system_prompt(QueryType.SUMMARIZATION)
    user_prompt = prompt_templates.format_user_prompt(
        f"Prepare a single paragraph summary of up to {SUMMARY_LENGTH} words. Return only the summary.",
        r"{context}",
        QueryType.SUMMARIZATION,
    )
    summaries = []
    async for chunk in get_chunk(doc_id):
        summaries.append(
            await get_model_response(
                system_prompt, user_prompt.format(context=chunk), client
            )
        )
        return await cascade_query(summaries, user_prompt, system_prompt, client)


@router.get("/short_description/{doc_id}")
async def get_short_description(
    doc_id: str,
    summary: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    system_prompt = prompt_templates.get_system_prompt(QueryType.SUMMARIZATION)
    user_prompt = f"""
    **DOCUMENT CONTEXT:**
    {summary}
    **QUERY REQUEST:** Return a short description of the document, up to {SHORT_DSECRIPTION_LENGTH} words.

    **INSTRUCTIONS:**
    Preserve the original meaning of the document while summarizing it into a concise description.
    Return only the short description.
    """

    return await get_model_response(user_prompt, system_prompt, client)


async def cascade_query(
    chunks: list[str],
    user_prompt: str,
    system_prompt: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    # Not ideal, will consume a lot of memory as prev chunks will not be gc till final set is gotten
    if len(chunks) == 1:
        return chunks[0]
    new_chunks = []
    for i in range(0, len(chunks), 8):
        new_chunk_context = "\n".join(chunks[i : i + 8])
        user_prompt = user_prompt.format(context=new_chunk_context)
        new_chunks.append(await get_model_response(user_prompt, system_prompt, client))

    return await cascade_query(new_chunks, user_prompt, system_prompt, client)


@router.get("/author/{doc_id}")
async def get_authors(
    doc_id: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    system_prompt = "If the question cannot be answered, return only the stop token."
    user_prompt = """
    **DOCUMENT CONTEXT:**
    {context}
    **QUERY REQUEST:** Identify the Authors in the given document

    **INSTRUCTIONS:**
    Return the list of authors in the following format:
    Author: Author1, Author2, Author3, etc
    """
    chunks = []
    async for chunk in get_chunk(doc_id):
        chunks.append(
            await get_model_response(
                system_prompt, user_prompt.format(context=chunk), client
            )
        )

    return await cascade_query(chunks, user_prompt, system_prompt, client)


@router.get("/title/{doc_id}")
async def get_title(
    doc_id: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    system_prompt = "If the question cannot be answered, return only the stop token."
    user_prompt = """
    **DOCUMENT CONTEXT:**
    {context}
    **QUERY REQUEST:** Identify the title in the given document. If the title cannot be found, generate one based on the contents of the document.

    **INSTRUCTIONS:**
    Return the title in the following format:
    Title: Title
    """
    chunks = []
    async for chunk in get_chunk(doc_id):
        chunks.append(
            await get_model_response(
                system_prompt, user_prompt.format(context=chunk), client
            )
        )
    for hunk in chunks:
        logger.info(hunk)
    return await cascade_query(chunks, user_prompt, system_prompt, client)


@router.get("/keywords/{doc_id}")
async def get_keywords(
    doc_id: str,
    client: AsyncOpenAI = Depends(get_openai_client),
):
    system_prompt = "If the question cannot be answered, return only the stop token."
    user_prompt = """
    **DOCUMENT CONTEXT:**
    {context}
    **QUERY REQUEST:** Identify the keywords in the given document.

    **INSTRUCTIONS:**
    Return the list of keywords in the following format:
    keywords: keyword1, keyword2, keyword3, etc
    """
    chunks = []
    async for chunk in get_chunk(doc_id):
        chunks.append(
            await get_model_response(
                system_prompt, user_prompt.format(context=chunk), client
            )
        )

    keywords = []
    for chunk in chunks:
        logger.info(chunk)
        keywords_split = chunk.split("keywords:")
        if len(keywords_split) <= 1:
            continue
        keywords.extend(keywords_split[-1].split(", "))
    return list(set(keywords))


@router.get("/filename/{doc_id}")
async def get_filename(doc_id: str):
    redis_filename_store = RedisStringStorage(prefix=FILENAME_REDIS_PREFIX)
    filename = redis_filename_store[doc_id]
    if not filename:
        raise HTTPException(status_code=404, detail="Filename not found for document")
    return filename


async def generate_metadata(
    doc_id: str,
):
    client = get_openai_client()
    try:
        summary = await get_summary(doc_id, client)
        metadata = {
            "filename": await get_filename(doc_id),
            "summary": summary,
            "exacutive_summary": await get_short_description(
                doc_id, summary["summary"], client
            ),
            "keywords": await get_keywords(doc_id, client),
            "authors": await get_authors(doc_id, client),
            "title": await get_title(doc_id, client),
        }
        save_job(
            doc_id=doc_id,
            job_data=metadata,
            status="completed",
            job_type="metadata",
        )
        return metadata
    except Exception as e:
        logger.error(f"Error generating metadata for {doc_id}: {e}", exc_info=True)
        error_job = {
            "doc_id": doc_id,
            "status": "error",
            "message": "Failed to download or generate metadata",
        }
        save_job(
            doc_id=doc_id, job_data=error_job, status="failed", job_type="extraction"
        )


@router.post("/", status_code=202)
async def submit_pdf(doc_id: str, background_tasks: BackgroundTasks):
    save_job(
        doc_id=doc_id,
        job_data={},
        status="processing",
        job_type="metadata",
    )

    background_tasks.add_task(generate_metadata, doc_id)
    return None


@router.get("/{doc_id}")
async def get_status(doc_id: str):
    job = load_job(doc_id=doc_id, job_type="metadata")
    if not job:
        raise HTTPException(status_code=404, detail="Document ID not found")

    if job.get("status") == "failed":
        error_message = job.get("data", {}).get("message", "Processing failed")
        raise HTTPException(status_code=500, detail=error_message)

    job_data = job.get("data", {})

    return {
        "doc_id": doc_id,
        "status": job.get("status", "unknown"),
        "metadata": job_data,
    }
