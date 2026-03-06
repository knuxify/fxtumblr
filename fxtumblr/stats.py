# SPDX-License-Identifier: MIT
"""Code for saving and exposing statistics."""

import asyncio
import hashlib

from . import config
from .cache import cache
from .render import RenderFiletype, RenderModifier
from .render.paths import get_render_cache_key

STATS_TIMEOUT = config.stats.timeout


class Statistics:
    """Object to keep track of statistics."""

    def __init__(self) -> None:
        """Initialize the Statistics object."""

        #: List of counter names.
        self.counters: list[str] = []

        #: Counter descriptions.
        self.counter_descriptions: dict[str, str] = {}

        # Register counters for posts
        self.register_counter("post_count", "Post embed count")
        self.register_counter("unique_post_count", "Unique post embed count")

        # Register counters for renders
        self.register_counter("render_count", "Post render count")
        self.register_counter("unique_render_count", "Unique post render count")

        # Register counters for errors
        self.register_counter("error_count", "Error count")
        self.register_counter("post_error_count", "Post fetching error count")
        self.register_counter("embed_error_count", "Embed generation error count")
        self.register_counter("api_error_count", "Tumblr API access error count")

        # Register counters for render errors
        self.register_counter("render_error_count", "Render error count")
        self.register_counter(
            "render_uncaught_error_count", "Render uncaught error count"
        )

    def register_counter(self, name: str, description: str):
        """Register a counter with the given name."""
        self.counters.append(name)
        self.counter_descriptions[name] = description

    async def get_counter(self, name: str) -> int:
        """
        Get the value of the counter with the given name.

        :param name: Name of counter to get the value of.
        :returns: The value of the counter as an integer; if the counter doesn't
            exist, 0 will be returned.
        """
        return int((await cache.get(f"fxt-stats:cnt:{name}")) or 0)

    async def increment_counter(self, name: str) -> int:
        """
        Increment the counter with the given name.

        :param name: Name of counter to increment.
        :returns: The new value of the counter.
        """
        ret = await cache.increment(f"fxt-stats:cnt:{name}")
        await cache.timeout(f"fxt-stats:cnt:{name}", STATS_TIMEOUT)
        return ret

    async def generate_prometheus_metrics(self):
        """
        Get the Prometheus data for the statistics.

        :returns: String containing Prometheus-compatible metrics data.
        """
        out = ""

        for counter in self.counters:
            description = self.counter_descriptions[counter]
            value = await self.get_counter(counter)
            out += f"# HELP {counter} {description}\n# TYPE {counter} counter\n{counter} {value}\n\n"

        return out

    async def get_post_hash(self, blog_id: str, post_id: int) -> str:
        """Get the unique anonymized hash for the given post."""

        def _get_post_hash(self, blog_id: str, post_id: int) -> str:
            return hashlib.sha256(f"{blog_id}-{post_id}".encode()).hexdigest()

        return await asyncio.to_thread(_get_post_hash, self, blog_id, post_id)

    async def register_post_hit(self, blog_id: str, post_id: int):
        """Register a hit for the post with the given identifier and post ID."""

        if config.stats.ignore_posts:
            for ignored_blog_id, ignored_post_id in config.stats.ignore_posts:
                if blog_id == ignored_blog_id and post_id == ignored_post_id:
                    return

        await self.increment_counter("post_count")

        # Post-specific cache key, used to determine uniqueness
        post_hash = await self.get_post_hash(blog_id, post_id)
        post_key = f"fxt-stats:post:{post_hash}"

        # If the post key does not exist in the cache, it is considered
        # unique; the key times out after 24 hours, so it will automatically
        # become non-unique 24 hours after it was first parsed.
        if not await cache.exists(post_key):
            await self.increment_counter("unique_post_count")
            await cache.set(post_key, "hit")
            # Post remains unique for 24 hours
            await cache.timeout(post_key, 60 * 60 * 24)

    async def get_render_hash(
        self,
        blog_id: str,
        post_id: int,
        modifiers: list[RenderModifier],
        filetype: RenderFiletype,
    ) -> str:
        """Get the unique anonymized hash for the given render."""

        def _get_post_hash(cache_key: str) -> str:
            return hashlib.sha256(cache_key.encode()).hexdigest()

        cache_key = get_render_cache_key(blog_id, post_id, modifiers, filetype)

        return await asyncio.to_thread(_get_post_hash, cache_key)

    async def register_render_hit(
        self,
        blog_name: str,
        post_id: int,
        modifiers: list[RenderModifier],
        filetype: RenderFiletype,
    ):
        """Register a hit for the render with the given parameters."""

        if config.stats.ignore_posts:
            for ignored_blog_id, ignored_post_id in config.stats.ignore_posts:
                if blog_name == ignored_blog_id and post_id == ignored_post_id:
                    return

        await self.increment_counter("render_count")

        render_hash = await self.get_render_hash(
            blog_name, post_id, modifiers, filetype
        )
        render_key = f"fxt-stats:render:{render_hash}"

        if not await cache.exists(render_key):
            await self.increment_counter("unique_render_count")
            await cache.set(render_key, "hit")
            # Render remains unique for 24 hours
            await cache.timeout(render_key, 60 * 60 * 24)


#: Global statistics object.
stats = Statistics()
