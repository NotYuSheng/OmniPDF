from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from openai import AsyncOpenAI, APIError
from shared_utils.openai_client import get_openai_client
from shared_utils.chroma_client import get_chunks
from shared_utils.redis import RedisDocumentFileList
from shared_utils.s3_utils import save_job, load_job
import logging
import os
from metadata_service.models.llm_config import (
    ModelConfig,
    PromptTemplates, 
    ModelResponseOptimizer
)

router = APIRouter(prefix="/metadata", tags=["metadata"])

logger = logging.getLogger(__name__)
document_list = RedisDocumentFileList()

model_config = ModelConfig()
prompt_templates = PromptTemplates()
response_optimizer = ModelResponseOptimizer()

OPENAI_MODEL_NAME = model_config.model_name
SUMMARY_LENGTH = int(os.getenv("SUMMARY_LENGTH", "500"))
SHORT_DSECRIPTION_LENGTH = int(os.getenv("SHORT_DSECRIPTION_LENGTH", "20"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "8"))
PROMPT_PURPOSE = ["default", "summary", "title", "keywords", "authors"]


async def get_model_response(
    system_prompt: str,
    user_prompt: str,
    client: AsyncOpenAI
):
    # Prepare messages for model
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
            **model_config.generation_params,
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
    
    # Post-process the response
    if model_config.enable_response_post_processing:
        processed_response = response_optimizer.post_process_llm_response(first_choice.message.content)
    else:
        processed_response = first_choice.message.content

    return processed_response


async def get_summary(
    chunks: list[str],
    client: AsyncOpenAI
):
    system_prompt = prompt_templates.get_system_prompt(PROMPT_PURPOSE[1])
    user_prompt = prompt_templates.get_user_prompt(
        f"Prepare a single paragraph summary of up to {SUMMARY_LENGTH} words. Return only the summary.", 
        PROMPT_PURPOSE[1],
        r"{context}"
    )
    summaries = []
    for chunk in chunks:
        summaries.append(
            await get_model_response(
                system_prompt, user_prompt.format(context=chunk), client
            )
        )
    return await cascade_query(summaries, user_prompt, system_prompt, client)


async def get_short_description(
    summary: str,
    client: AsyncOpenAI
):
    system_prompt = prompt_templates.get_system_prompt(PROMPT_PURPOSE[1])
    user_prompt = prompt_templates.get_user_prompt(
        f"Return a short description of the document, up to {SHORT_DSECRIPTION_LENGTH} words. Return only the short description.",
        PROMPT_PURPOSE[1],
        summary
    )

    return await get_model_response(system_prompt, user_prompt, client)


async def cascade_query(
    chunks: list[str],
    user_prompt: str,
    system_prompt: str,
    client: AsyncOpenAI
):
    if not chunks:
        return ""
    # Not ideal, will consume a lot of memory as prev chunks will not be gc till final set is gotten
    if len(chunks) == 1:
        return chunks[0]
    
    current_chunks = chunks
    while len(current_chunks) > 1:
        new_chunks = []
        for i in range(0, len(current_chunks), BATCH_SIZE):
            new_chunk_context = "\n".join(current_chunks[i : i + BATCH_SIZE])
            user_prompt_with_context = user_prompt.format(context=new_chunk_context)
            new_chunks.append(await get_model_response(system_prompt, user_prompt_with_context, client))
        current_chunks = new_chunks
        logger.info(f"Reduced to {len(current_chunks)} chunks.")

    return current_chunks[0]


async def get_authors(
    chunks: list[str],
    client: AsyncOpenAI
):
    system_prompt = prompt_templates.get_system_prompt(PROMPT_PURPOSE[0])
    user_prompt = prompt_templates.get_user_prompt(
        "Identify the Authors in the given document", PROMPT_PURPOSE[4], r"{context}"
    )

    author_chunks = []
    for chunk in chunks:
        author_chunks.append(
            await get_model_response(
                system_prompt, user_prompt.format(context=chunk), client
            )
        )

    authors = []
    for chunk in author_chunks:
        logger.info(chunk)
        author_split = chunk.split(":")
        if author_split[0].lower() != "authors":
            logger.info(author_split)
            continue
        authors.extend([author.strip() for author in author_split[-1].split(",")])
    return list(set(authors))


async def get_title(
    chunks: list[str],
    client: AsyncOpenAI
):
    system_prompt = prompt_templates.get_system_prompt(PROMPT_PURPOSE[0])
    user_prompt = prompt_templates.get_user_prompt(
        "Identify the title in the given document", PROMPT_PURPOSE[2], r"{context}"
    )
    
    title_chunks = []
    for chunk in chunks:
        title_chunks.append(
            await get_model_response(
                system_prompt, user_prompt.format(context=chunk), client
            )
        )
    title_str = await cascade_query(title_chunks, user_prompt, system_prompt, client)
    
    title_split = title_str.split(":")
    if title_split[0].lower() != "title":
        return "UNKNOWN"
    return title_split[-1]


async def get_keywords(
    chunks: list[str],
    client: AsyncOpenAI
):
    system_prompt = prompt_templates.get_system_prompt(PROMPT_PURPOSE[0])
    user_prompt = prompt_templates.get_user_prompt(
        "Identify the Keywords in the given document", PROMPT_PURPOSE[3], r"{context}"
    )
    
    keyword_chunks = []
    for chunk in chunks:
        keyword_chunks.append(
            await get_model_response(
                system_prompt, user_prompt.format(context=chunk), client
            )
        )

    keywords = []
    for chunk in keyword_chunks:
        logger.info(chunk)
        keywords_split = chunk.split(":", 1)
        if keywords_split[0].lower() != "keywords":
            continue
        keywords.extend([keyword.strip() for keyword in keywords_split[-1].split(",")])
    return list(set(keywords))


async def get_filename(doc_id: str):
    filename = document_list.get_document_name(doc_id)
    if not filename:
        raise HTTPException(status_code=404, detail="Filename not found for document")
    return filename


async def generate_metadata(
    doc_id: str,
    client: AsyncOpenAI
):
    chunks = await get_chunks(doc_id)
    try:
        summary = await get_summary(chunks, client)
        logger.info(summary)
        metadata = {
            "filename": await get_filename(doc_id),
            "summary": summary,
            "executive_summary": await get_short_description(
                summary, client
            ),
            "keywords": await get_keywords(chunks, client),
            "authors": await get_authors(chunks, client),
            "title": await get_title(chunks, client),
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
            doc_id=doc_id, job_data=error_job, status="failed", job_type="metadata"
        )


@router.post("/{doc_id}", status_code=202)
async def submit_pdf(doc_id: str, background_tasks: BackgroundTasks, client: AsyncOpenAI = Depends(get_openai_client)):
    save_job(
        doc_id=doc_id,
        job_data={},
        status="processing",
        job_type="metadata",
    )

    background_tasks.add_task(generate_metadata, doc_id, client)
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
