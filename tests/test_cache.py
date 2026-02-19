# SPDX-License-Identifier: MIT
"""Test the cache access object."""

import asyncio

import pytest
from fakeredis import FakeAsyncRedis, FakeServer

from fxtumblr.cache import Cache


@pytest.fixture
def cache() -> Cache:  # noqa: F811
    """Generate a cache object fixture."""

    # Provide dummy connection values, we override the server later
    cache = Cache("", 0)

    redis_server = FakeServer()
    cache.cache = FakeAsyncRedis(server=redis_server, decode_responses=True)
    cache.cache_bin = FakeAsyncRedis(server=redis_server, decode_responses=False)

    return cache


@pytest.mark.asyncio
async def test_cache_ping(cache):
    """Test the cache ping function."""
    assert await cache.ping() is True


@pytest.mark.asyncio
async def test_cache_text(cache):
    """Test basic text caching functions."""
    await cache.set("fxt-test:1", "test!", 2)
    assert await cache.exists("fxt-test:1")
    assert await cache.get("fxt-test:1") == "test!"

    # Test timeout
    await asyncio.sleep(3)
    assert not await cache.exists("fxt-test:1")
    assert await cache.get("fxt-test:1") is None

    # Test unknown key
    assert await cache.get("fxt-test:unknown") is None
    assert not await cache.exists("fxt-test:unknown")

    # Test delete
    await cache.set("fxt-test:1:removeme", "test!", 10)
    await cache.delete("fxt-test:1:removeme")
    assert not await cache.exists("fxt-test:1:removeme")
    assert not await cache.get("fxt-test:1:removeme")


@pytest.mark.asyncio
async def test_cache_json(cache):
    """Test JSON caching functions."""
    await cache.set_json("fxt-test:2", {"a": 1, "b": "test"}, 2)
    assert await cache.exists("fxt-test:2")
    assert await cache.get_json("fxt-test:2") == {"a": 1, "b": "test"}

    # Test timeout
    await asyncio.sleep(3)
    assert not await cache.exists("fxt-test:2")
    assert await cache.get_json("fxt-test:2") is None

    # Test unknown key
    assert await cache.get_json("fxt-test:unknown") is None

    # Test delete
    await cache.set_json("fxt-test:2:removeme", {"a": 2}, 10)
    await cache.delete("fxt-test:2:removeme")
    assert not await cache.exists("fxt-test:2:removeme")
    assert not await cache.get_json("fxt-test:2:removeme")


@pytest.mark.asyncio
async def test_cache_bin(cache):
    """Test binary caching functions."""
    await cache.set_bin("fxt-test:3", "test".encode("utf-8"), 2)
    assert await cache.exists("fxt-test:3")
    assert await cache.get_bin("fxt-test:3") == "test".encode("utf-8")

    # Test timeout
    await asyncio.sleep(3)
    assert not await cache.exists("fxt-test:3")
    assert await cache.get_bin("fxt-test:3") is None

    # Test unknown key
    assert await cache.get_bin("fxt-test:unknown") is None

    # Test delete
    await cache.set_bin("fxt-test:3:removeme", "abc".encode("utf-8"), 10)
    await cache.delete("fxt-test:3:removeme")
    assert not await cache.exists("fxt-test:3:removeme")
    assert not await cache.get_bin("fxt-test:3:removeme")


@pytest.mark.asyncio
async def test_cache_increment(cache):
    """Test the cache increment function."""
    await cache.set("fxt-test:number", "1", 0)
    assert await cache.increment("fxt-test:number")
    assert await cache.get("fxt-test:number") == "2"


@pytest.mark.asyncio
async def test_cache_timeout(cache):
    """Test the cache timeout function."""
    await cache.set("fxt-test:timeout", "1", 0)
    assert await cache.timeout("fxt-test:timeout", 2)
    await asyncio.sleep(3)
    assert await cache.exists("fxt-test:timeout") is False
    assert await cache.get("fxt-test:timeout") is None
