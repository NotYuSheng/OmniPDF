import asyncio
import logging

from shared_utils.redis import (
    RedisBase,
    RedisDocumentFileList,
    RedisSetStorage,
    RedisPrefix,
    SEPERATOR,
)
from shared_utils.s3_utils import delete_files
from shared_utils.chroma_client import get_chroma_client

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
    logger.info(f"deleting session_id: {prefixed_session_id}")
    prefixed_keys = [document_files.flag_prefixed(doc_id) for doc_id in redis_set_store[prefixed_session_id]]
    redis_store.delete_set(prefixed_keys)
    del redis_set_store[prefixed_session_id]


async def handle_doc_file_list(prefixed_doc_id: str):
    logger.info(f"deleting doc file list for doc_id: {prefixed_doc_id}")
    delete_files(redis_set_store[prefixed_doc_id])
    doc_id = get_key_from_prefixed(prefixed_doc_id)
    await clean_chromadb(doc_id)
    del redis_set_store[prefixed_doc_id]


async def clean_chromadb(doc_id):
    chroma_client = await get_chroma_client()
    
    async def delete_from_collection(collection_name):
        collection = await chroma_client.get_or_create_collection(name=collection_name)
        await collection.delete(where={"doc_id": doc_id})
        logger.info(f"Deleted documents with doc_id '{doc_id}' from collection '{collection_name}'")
    
    # Process all collections concurrently using asyncio.gather
    await asyncio.gather(*[
        delete_from_collection(collection_name) 
        for collection_name in EMBEDDING_COLLECTIONS
    ])


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
    if any(event in msg_origin for event in REMOVAL_EVENTS):
        msg_data: str = msg["data"]
        try:
            flag, key = msg_data.split(SEPERATOR, maxsplit=1)
            logger.info(f"Handling {msg_origin} for {flag} with key {key}")
            runner.run(DELETION_PREFIX_CALLBACK_DICT.get(flag, empty_function)(key))
        except ValueError as e:
            logger.warning(f"Skipping deletion due to malformed data. {e}")


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
