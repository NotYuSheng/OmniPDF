import asyncio
import logging
import time

from shared_utils.redis_utils import (
    RedisBase,
    RedisDocumentFileList,
    RedisSetStorage,
    RedisPrefix,
    SEPERATOR,
)
from shared_utils.s3_utils import delete_files
from shared_utils.chroma_client import get_chroma_client
from .metrics import (
    sessions_cleaned_total,
    documents_cleaned_total,
    files_deleted_total,
    chromadb_collections_cleaned_total,
    redis_events_processed_total,
    cleanup_duration_seconds,
    cleanup_errors_total
)

logger = logging.getLogger(__name__)
runner = asyncio.Runner()

redis_store = RedisBase()
document_files = RedisDocumentFileList(redis_client=redis_store.client)
redis_set_store = RedisSetStorage(redis_client=document_files.client)
pubsub = redis_store.client.pubsub()

# UNABLE TO HANDLE srem AND OTHERS DUE TO ONLY HAVING EVENT AND KEY INFO
REMOVAL_EVENTS = ["del", "expired"]
SEMANTIC_EMBEDDING_COLLECTION = "SemanticEmbeds"
TEXTUAL_EMBEDDING_COLLECTION = "SentenceEmbeds"
EMBEDDING_COLLECTIONS = [SEMANTIC_EMBEDDING_COLLECTION, TEXTUAL_EMBEDDING_COLLECTION]


def get_key_from_prefixed(prefixed_key: str) -> str:
    try:
        _, key = prefixed_key.split(SEPERATOR, maxsplit=1)
        return key
    except ValueError:
        logger.warning(f"Could not split prefixed key: {prefixed_key}")
        return prefixed_key


async def empty_function(_):
    logger.info("Empty function called")
    pass


async def handle_session_doc_list(prefixed_session_id: str):
    start_time = time.time()
    try:
        logger.info(f"deleting session_id: {prefixed_session_id}")
        prefixed_keys = [
            document_files.flag_prefixed(doc_id)
            for doc_id in redis_set_store[prefixed_session_id]
        ]
        redis_store.delete_set(prefixed_keys)
        del redis_set_store[prefixed_session_id]
        
        # Track successful session cleanup
        sessions_cleaned_total.inc()
        cleanup_duration_seconds.labels(cleanup_type="session").observe(time.time() - start_time)
        
    except Exception as e:
        logger.error(f"Error cleaning session {prefixed_session_id}: {e}")
        cleanup_errors_total.labels(error_type="session_cleanup").inc()
        raise


async def handle_doc_file_list(prefixed_doc_id: str):
    start_time = time.time()
    try:
        logger.info(f"deleting doc file list for doc_id: {prefixed_doc_id}")
        
        # Get file list and delete files
        file_list = redis_set_store[prefixed_doc_id]
        delete_files(file_list)
        files_deleted_total.inc(len(file_list))
        
        # Clean ChromaDB
        doc_id = get_key_from_prefixed(prefixed_doc_id)
        await clean_chromadb(doc_id)
        
        # Clean Redis
        del redis_set_store[prefixed_doc_id]
        
        # Track successful document cleanup
        documents_cleaned_total.inc()
        cleanup_duration_seconds.labels(cleanup_type="document").observe(time.time() - start_time)
        
    except Exception as e:
        logger.error(f"Error cleaning document {prefixed_doc_id}: {e}")
        cleanup_errors_total.labels(error_type="document_cleanup").inc()
        raise


async def clean_chromadb(doc_id):
    chroma_client = await get_chroma_client()

    async def delete_from_collection(collection_name):
        try:
            collection = await chroma_client.get_or_create_collection(name=collection_name)
            await collection.delete(where={"doc_id": doc_id})
            logger.info(
                f"Deleted documents with doc_id '{doc_id}' from collection '{collection_name}'"
            )
            # Track successful ChromaDB collection cleanup
            chromadb_collections_cleaned_total.labels(collection_name=collection_name).inc()
        except Exception as e:
            logger.error(f"Error cleaning ChromaDB collection {collection_name}: {e}")
            cleanup_errors_total.labels(error_type="chromadb_cleanup").inc()
            raise

    # Process all collections concurrently using asyncio.gather
    await asyncio.gather(
        *[
            delete_from_collection(collection_name)
            for collection_name in EMBEDDING_COLLECTIONS
        ]
    )


DELETION_PREFIX_CALLBACK_DICT = {
    RedisPrefix.DOC_FLAG: handle_doc_file_list,
    RedisPrefix.SESSION_FLAG: handle_session_doc_list,
}


def event_handler(msg):
    logger.info(
        f"handler -- {msg['type']} {msg['pattern']}) from {msg['channel']}: {msg['data']}"
    )
    if msg["type"] != "pmessage":
        return
    
    msg_origin = msg["channel"]
    
    # Track Redis events processed
    if any(event in msg_origin for event in REMOVAL_EVENTS):
        event_type = next((event for event in REMOVAL_EVENTS if event in msg_origin), "unknown")
        redis_events_processed_total.labels(event_type=event_type).inc()
        
        msg_data: str = msg["data"]
        try:
            flag, key = msg_data.split(SEPERATOR, maxsplit=1)
            logger.info(f"Handling {msg_origin} for {flag} with key {key}")
            runner.run(DELETION_PREFIX_CALLBACK_DICT.get(flag, empty_function)(key))
        except ValueError as e:
            logger.warning(f"Skipping deletion due to malformed data. {e}")
            cleanup_errors_total.labels(error_type="malformed_data").inc()


def setup_redis_watcher_thread():
    redis_store.client.config_set("notify-keyspace-events", "Egsx")
    sub_key = "__key*__:*"
    pubsub.psubscribe(**{sub_key: event_handler})
    logger.info(pubsub.patterns)
    logger.info(pubsub.channels)
    logger.info("Competed setup")
    return pubsub.run_in_thread()


if __name__ == "__main__":
    redis_store.client.config_set("notify-keyspace-events", "Egsx")
    sub_key = "__key*__:*"
    pubsub.psubscribe(**{sub_key: event_handler})
    logger.info("setup complete")
    for msg in pubsub.listen():
        pass
