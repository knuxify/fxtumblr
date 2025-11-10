# SPDX-License-Identifier: MIT
"""Cache handling functions and tasks."""

import json
from typing import Union

import redis.asyncio as redis

from . import config

#: Default cache timeout.
DEFAULT_TIMEOUT: int = config.get("cache", {}).get("timeout", 360)


class Cache:
    """Class representing Redis cache."""

    def __init__(self):
        """Initialize the Cache object."""

        #: Redis configuration.
        self.cache = redis.Redis(
            host=config["redis"]["host"],
            port=config["redis"]["port"],
            password=config["redis"].get("password", None),
            decode_responses=True,
        )

        #: Redis configuration without decoded responses.
        self.cache_bin = redis.Redis(
            host=config["redis"]["host"],
            port=config["redis"]["port"],
            password=config["redis"].get("password", None),
            decode_responses=False,
        )

    async def _set(
        self, cache: redis.Redis, key: str, value: Union[str, bytes], timeout: int = 0
    ):
        await cache.set(key, value)

        if timeout != 0:
            await cache.expire(key, timeout)
        else:
            await cache.persist(key)

    async def get(self, key: str) -> Union[str, None]:
        """Get element by key, as a string."""
        return await self.cache.get(key)

    async def set(self, key: str, value: str, timeout: int = DEFAULT_TIMEOUT):
        """Set the element with the given key to the given string value."""
        return await self._set(self.cache, key, value, timeout)

    async def get_bin(self, key: str) -> Union[bytes, None]:
        """Get element by key, as bytes."""
        return await self.cache_bin.get(key)

    async def set_bin(self, key: str, value: bytes, timeout: int = DEFAULT_TIMEOUT):
        """Set the element with the given key to the given bytes value."""
        return await self._set(self.cache_bin, key, value, timeout)

    async def get_json(self, key: str) -> Union[dict, None]:
        """Get deserialized JSON value from the cache."""
        raw = await self.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, value: dict, timeout: int = DEFAULT_TIMEOUT):
        """Set dict serialized to JSON as the cache value for the given key."""
        serialized = json.dumps(value)
        return await self.set(key, serialized, timeout)

    async def delete(self, key: str) -> None:
        """Delete element from the cache."""
        await self.cache.delete(key)

    async def ping(self) -> bool:
        """Test the connection to Redis."""
        return bool(await self.cache.ping())

    async def increment(self, key: str) -> int:
        """
        Increment a numerical key.

        :returns: The new value.
        """
        return await self.cache.incr(key)

    async def timeout(self, key: str, timeout: int):
        """Set timeout for the given key."""
        return await self.cache.expire(key, timeout)


#: Global cache access object.
cache = Cache()
