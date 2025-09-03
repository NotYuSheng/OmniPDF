import asyncio
import logging

from fastapi import HTTPException
from utils.proxy import load_or_create_extraction_job, load_or_create_semantic_embedder_job, load_or_create_sentence_embedder_job, load_or_create_metadata_job
from shared_utils.job_status import JobType

logger = logging.getLogger(__name__)

POLLING_DELAY = 10


async def wait_for_extraction(doc_id: str):
    job = None
    while not job:
        try:
            job = await load_or_create_extraction_job(doc_id)
        except HTTPException as e:
            if e.status_code != 202:
                if e.status_code == 450:
                    logger.error(f"Failed to process {doc_id} for {JobType.EXTRACTION}. Please refer to file or service logs for more info.")
                else:
                    logger.error(f"An unknown error has occur for {doc_id}")
                break
        await asyncio.sleep(POLLING_DELAY)



async def wait_for_semantic_embedder(doc_id: str, session_id: str):
    job = None
    while not job:
        try:
            job = await load_or_create_semantic_embedder_job(doc_id, session_id)
        except HTTPException as e:
            if e.status_code != 202:
                if e.status_code == 450:
                    logger.error(f"Failed to process {doc_id} for {JobType.SEMANTICEMBEDDER}. Please refer to file or service logs for more info.")
                else:
                    logger.error(f"An unknown error has occur for {doc_id}")
                break
        await asyncio.sleep(POLLING_DELAY)


                
async def wait_for_sentence_embedder(doc_id: str, session_id: str):
    job = None
    while not job:
        try:
            job = await load_or_create_sentence_embedder_job(doc_id, session_id)
        except HTTPException as e:
            if e.status_code != 202:
                if e.status_code == 450:
                    logger.error(f"Failed to process {doc_id} for {JobType.SENTENCEEMBEDDER}. Please refer to file or service logs for more info.")
                else:
                    logger.error(f"An unknown error has occur for {doc_id}")
                break
        await asyncio.sleep(POLLING_DELAY)

                
async def wait_for_metadata(doc_id: str, session_id: str):
    job = None
    while not job:
        try:
            job = await load_or_create_metadata_job(doc_id, session_id)
        except HTTPException as e:
            if e.status_code != 202:
                if e.status_code == 450:
                    logger.error(f"Failed to process {doc_id} for {JobType.METADATA}. Please refer to file or service logs for more info.")
                else:
                    logger.error(f"An unknown error has occur for {doc_id}")
                break
        await asyncio.sleep(POLLING_DELAY)


async def process_file_basic(doc_id: str, session_id: str):
    await wait_for_extraction(doc_id)
    await asyncio.gather(
        wait_for_semantic_embedder(doc_id, session_id),
        wait_for_sentence_embedder(doc_id, session_id),
    )
    await wait_for_metadata(doc_id, session_id)
    logger.info(f"Completed basic Processing for {doc_id}")