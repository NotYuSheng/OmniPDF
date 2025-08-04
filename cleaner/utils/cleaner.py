import logging

from shared_utils.redis import RedisBase, RedisSetStorage, SEPERATOR
from shared_utils.s3_utils import delete_file

logger = logging.getLogger(__name__)

redis_store = RedisBase()
pubsub = redis_store.client.pubsub()

# UNABLE TO HANDLE srem AND OTHERS DUE TO ONLY HAVING EVENT AND KEY INFO
REMOVAL_EVENTS = ["del", "expired"]


def empty_function(_):
    pass


def clean_redis_key(key: str):
    logger.info(f"deleting redis {key}")
    del redis_store[key]


def clean_s3_files(key: str):
    logger.info(f"deleting s3 {key}")
    redis_set_store = RedisSetStorage(redis_client=redis_store.client)
    for doc_key in redis_set_store[key]:
        if doc_key:
            logger.info(f"deleting {doc_key}")
            delete_file(doc_key)
    del redis_set_store[key]


def clean_s3_file(key: str):
    logger.info(f"deleting {key}")
    delete_file(key)


def clean_chromadb(key):
    pass


DELETION_PREFIX_CALLBACK_DICT = {
    "S3Key": clean_s3_files,
    "SessionHeader": clean_s3_files,
    "S3_File": clean_s3_file,
    "RedisKey": clean_redis_key,
    "ChromaDBKey": clean_chromadb,
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
