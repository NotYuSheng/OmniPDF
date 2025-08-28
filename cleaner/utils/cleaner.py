import logging

from shared_utils.redis import RedisBase, RedisPrefix, RedisSetStorage, SEPERATOR
from shared_utils.s3_utils import delete_file, delete_folder, get_job_s3_key
from shared_utils.chroma_client import get_chroma_client

logger = logging.getLogger(__name__)

redis_store = RedisBase()
pubsub = redis_store.client.pubsub()

# UNABLE TO HANDLE srem AND OTHERS DUE TO ONLY HAVING EVENT AND KEY INFO
REMOVAL_EVENTS = ["del", "expired"]
SEMANTIC_EMBEDDING_COLLECTION = "SemanticEmbeds"
TEXTUAL_EMBEDDING_COLLECTION = "SentenceEmbeds"
EMBEDDING_COLLECTIONS = [SEMANTIC_EMBEDDING_COLLECTION, TEXTUAL_EMBEDDING_COLLECTION]

def empty_function(_):
    pass


def clean_redis_key(key: str):
    logger.info(f"deleting redis {key}")
    del redis_store[key]


def clean_s3_files(key: str):
    logger.info(f"deleting s3 files by filenames: {key}")
    redis_set_store = RedisSetStorage(redis_client=redis_store.client)
    for doc_key in redis_set_store[key]:
        if doc_key:
            logger.info(f"deleting {doc_key}")
            delete_file(doc_key)
    del redis_set_store[key]


def clean_s3_folder(key: str):
    logger.info(f"deleting s3 files by folder: {key}")
    redis_set_store = RedisSetStorage(redis_client=redis_store.client)
    for doc_key in redis_set_store[key]:
        if doc_key:
            logger.info(f"deleting {doc_key}")
            delete_folder(doc_key)
            delete_file(get_job_s3_key(doc_key, "extraction"))
    del redis_set_store[key]


def clean_s3_file(key: str):
    logger.info(f"deleting {key}")
    delete_file(key)


async def clean_chromadb(key):
    chroma_client = await get_chroma_client()
    for collection_name in EMBEDDING_COLLECTIONS:
        collection = await chroma_client.get_or_create_collection(name=collection_name)
        await collection.delete(where={"doc_id": key})

DELETION_PREFIX_CALLBACK_DICT = {
    RedisPrefix.SESSION_DOC_LIST: clean_s3_files,
    RedisPrefix.DOC_FLAG: clean_s3_folder,
    RedisPrefix.FILEPATH: clean_s3_file,
    RedisPrefix.SESSION_FLAG: clean_redis_key,
    RedisPrefix.CHROMADB: clean_chromadb,
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
            DELETION_PREFIX_CALLBACK_DICT.get(flag, empty_function)(key)
        except ValueError:
            logger.warning(f"Could not split message data, malformed key: {msg_data}")


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
