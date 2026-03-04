# SPDX-License-Identifier: MIT
"""Client code for communicating with the render server."""

import asyncio
import json
from typing import Any

import aiofiles
import aiofiles.os

from .. import config
from ..cache import cache
from . import RenderFiletype, RenderModifier
from .paths import get_render_cache_key, get_render_path


class RenderClient:
    """Render client connection class."""

    def __init__(self, host: str, port: int):
        """Initialize the render client access class."""
        self.host: str = host
        self.port: int = port

    async def send_message(self, data: dict) -> Any:
        """Send a message to the render server."""
        payload = json.dumps(data)

        reader, writer = await asyncio.open_connection(self.host, self.port)

        writer.write(payload.encode("utf-8"))
        await writer.drain()

        return await reader.read()

    async def render_post(
        self,
        blog_name: str,
        post_id: int,
        modifiers: list[RenderModifier],
        filetype: RenderFiletype,
        skip_cache: bool = False,
    ) -> bytes:
        """
        Get a render for the given post with the given parameters.

        If the render is cached, return it from the cache (unless skip_cache is set); otherwise queue a new render and return its contents.

        :param blog_name: Blog name of poster.
        :param post_id: ID of the post.
        :param modifiers: List of render modifiers.
        :param filetype: Filetype of the render.
        :param skip_cache: If True, forces a new render.
        :returns: Bytes object containing the response.
        """

        if not skip_cache:
            # Try to find the render in the cache.

            # Get from memory cache, if applicable
            if config.render.mem_cache_timeout:
                cache_key = get_render_cache_key(
                    blog_name, post_id, modifiers, filetype
                )
                ret = await cache.get_bin(cache_key)
                if ret:
                    return ret

            # Get from disk cache, if applicable
            if config.render.disk_cache_timeout:
                render_path = get_render_path(blog_name, post_id, modifiers, filetype)

                if await aiofiles.os.path.exists(render_path):
                    async with aiofiles.open(render_path, "rb") as render_file:
                        return await render_file.read()

        # If there is no cache hit, send a render request and return the result
        return await self.send_message(
            {
                "task_type": "post",
                "blog_name": blog_name,
                "post_id": post_id,
                "modifiers": [str(mod) for mod in modifiers],
                "filetype": str(filetype),
            }
        )


#: Global render client access class.
render_client = RenderClient(config.render.host, config.render.port)
