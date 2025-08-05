# Original code from https://github.com/duyixian1234/fastapi-redis-session
# Updated for package versions listed in requirements.txt

from os import getenv
from datetime import timedelta
from typing import Any, Generator
import logging
import json

from redis import Redis


logger = logging.getLogger(__name__)


class Config:
    redis_url: str = getenv("REDIS_URL")
    expire_time: timedelta = timedelta(hours=24)


config = Config()
SEPERATOR = ":"


class RedisBase:
    def __init__(
        self,
        redis_client=None,
        prefix="",
        default_expiry: timedelta | None = config.expire_time,
    ):
        self.client = redis_client if redis_client else Redis.from_url(config.redis_url)
        self.prefix = prefix
        self.default_expiry = default_expiry

    def __delitem__(self, key: str):
        self.client.delete(self.prefixed(key))

    def __contains__(self, key: str):
        return self.client.exists(self.prefixed(key))
    
    def prefixed(self, key: str):
        return f"{self.prefix}{SEPERATOR}{key}" if self.prefix else key


# Stores the data as string
class RedisStringStorage(RedisBase):
    def __getitem__(self, key: str):
        return self.client.getex(self.prefixed(key), self.default_expiry)

    def __setitem__(self, key: str, value: str):
        self.client.set(
            self.prefixed(key),
            value,
            ex=self.default_expiry,
        )


# Stores the data as string using json
class RedisJSONStorage(RedisStringStorage):
    def __getitem__(self, key: str):
        raw = super().__getitem__(key)
        if not raw:
            logger.info(f"Trying to load empty key {key}.")
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON data for {key}: {e}")
            raise e

    def __setitem__(self, key: str, value: Any):
        super().__setitem__(key, json.dumps(value))


class RedisSetStorage(RedisBase):
    def __init__(self, redis_client=None, prefix="", default_expiry=config.expire_time):
        super().__init__(redis_client, prefix, default_expiry)
        self.pipeline = self.client.pipeline()

    def __getitem__(self, key: str) -> set[str]:
        if self.default_expiry is not None:
            self.pipeline.expire(self.prefixed(key), self.default_expiry)
        self.pipeline.smembers(self.prefixed(key))
        members = self.pipeline.execute()[-1]
        return members

    def __setitem__(self, key: str, values: set):
        if not isinstance(values, set):
            raise ValueError("Set Expected. Right Hand Value should be a set.")
        self.pipeline.delete(self.prefixed(key))
        for value in values:
            self.pipeline.sadd(self.prefixed(key), value)
        self.pipeline.execute()

    def add(self, key: str, value: str):
        self.pipeline.sadd(self.prefixed(key), value)
        if self.default_expiry is not None:
            self.pipeline.expire(self.prefixed(key), self.default_expiry)
        self.pipeline.execute()

    def contains(self, key: str, value: str) -> bool:
        return self.client.sismember(self.prefixed(key), value)

    def remove(self, key: str, value: str):
        self.pipeline.srem(self.prefixed(key), value)
        if self.default_expiry is not None:
            self.pipeline.expire(self.prefixed(key), self.default_expiry)
        self.pipeline.execute()


class RedisSimpleFileFlag(RedisStringStorage):
    def __init__(self, redis_client=None, prefix="S3_File:", default_expiry = timedelta(hours=1)):
        super().__init__(redis_client, prefix, default_expiry)

    def set(self, key: str):
        self[key] = 1

    def clear(self, key: str):
        del self[key]


class RedisSetWithFlagExpiry(RedisSetStorage):
    # Do not use unless a clean up is set
    def __init__(
        self,
        redis_client=None,
        prefix="",
        flag_prefix="Set_Flag:",
        default_expiry=config.expire_time,
    ):
        super().__init__(redis_client, prefix, None)
        self.flag_expiry = default_expiry
        self.flag_prefix = flag_prefix

    def __delitem__(self, key: str):
        self.client.delete(self.flag_prefixed(key))

    def __contains__(self, key: str):
        return self.client.exists(self.flag_prefixed(key))

    def __getitem__(self, key: str):
        self.pipeline.getex(self.flag_prefixed(key), ex=self.flag_expiry)
        return super().__getitem__(key)
    
    def __setitem__(self, key: str, values: set):
        if key not in self:
            self.init(key)
        super().__setitem__(key, values)
    
    def init(self, key: str):
        self.client.set(self.flag_prefixed(key), 1, ex=self.flag_expiry)

    def add(self, key: str, value: str):
        self.pipeline.expire(self.flag_prefixed(key), self.flag_expiry)
        return super().add(key, value)

    def remove(self, key: str, value: str):
        self.pipeline.expire(self.flag_prefixed(key), self.flag_expiry)
        return super().remove(key, value)

    def flag_prefixed(self, key: str):
        return self.flag_prefix + SEPERATOR + self.prefixed(key)

def get_json_storage() -> Generator:
    storage = RedisJSONStorage()
    yield storage


def get_set_storage() -> Generator:
    service_cache = RedisSetStorage()
    yield service_cache


def get_string_storage() -> Generator:
    service_cache = RedisStringStorage()
    yield service_cache
