import asyncio
import logging

from fastapi import HTTPException
from utils.proxy import load_or_create_extraction_job, load_or_create_semantic_embedder_job, load_or_create_sentence_embedder_job, load_or_create_metadata_job
from shared_utils.job_status import JobType

logger = logging.getLogger(__name__)

POLLING_DELAY = 10

async def _wait_for_job(load_or_create_func, job_type, *args):
    job = None
    while not job:
        try:
            job = await load_or_create_func(*args)
        except HTTPException as e:
            if e.status_code != 202:
                if e.status_code == 450:
                    logger.error(f"Failed to process {args[0]} for {job_type}. Please refer to file or service logs for more info.")
                else:
                    logger.error(f"An unknown error has occurred for {args[0]}: {e}")
                break
        await asyncio.sleep(POLLING_DELAY)


async def wait_for_extraction(doc_id: str):
    await _wait_for_job(load_or_create_extraction_job, JobType.EXTRACTION, doc_id)


async def wait_for_semantic_embedder(doc_id: str, session_id: str):
    await _wait_for_job(load_or_create_semantic_embedder_job, JobType.SEMANTICEMBEDDER, doc_id, session_id)


async def wait_for_sentence_embedder(doc_id: str, session_id: str):
    await _wait_for_job(load_or_create_sentence_embedder_job, JobType.SENTENCEEMBEDDER, doc_id, session_id)


async def wait_for_metadata(doc_id: str, session_id: str):
    await _wait_for_job(load_or_create_metadata_job, JobType.METADATA, doc_id, session_id)


async def process_file_basic(doc_id: str, session_id: str):
    await wait_for_extraction(doc_id)
    await asyncio.gather(
        wait_for_semantic_embedder(doc_id, session_id),
        wait_for_sentence_embedder(doc_id, session_id),
    )
    await wait_for_metadata(doc_id, session_id)
    logger.info(f"Completed basic Processing for {doc_id}")