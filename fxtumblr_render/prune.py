# SPDX-License-Identifier: MIT
"""Code for pruning old renders from the disk cache in the background."""

import asyncio
import os
import time

import aiofiles.os

from . import config


async def prune_renders_thread():
    """Loop and repeatedly prune old renders."""
    while True:
        files = [
            os.path.join(config.render.path, filename)
            for filename in await aiofiles.os.listdir(config.render.path)
        ]

        current_time = time.time()
        max_time = current_time - config.render.disk_cache_timeout

        for path in files:
            # We do an extra check for last access time to prevent renders
            # getting removed midway through reading
            if (await aiofiles.os.path.getmtime(path) >= max_time) and (
                await aiofiles.os.path.getatime(path) < (current_time + 3.0)
            ):
                await aiofiles.os.remove(path)

        await asyncio.sleep(config.render.disk_cache_timeout)
