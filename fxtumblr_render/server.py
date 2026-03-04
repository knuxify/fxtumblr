# SPDX-License-Identifier: MIT
"""Main server loop and handling code."""

import asyncio
import json
import time
import traceback
from dataclasses import dataclass
from typing import Any

from fxtumblr.tumblr import TumblrAPI

from . import config
from .browser import Browser, get_browser
from .render import RenderTask


@dataclass
class Worker:
    """Single render worker."""

    #: Parent server of the worker.
    server: "Server"

    #: Asyncio task bound to this worker.
    task: asyncio.Task | None = None

    @property
    def browser(self):
        """Shorthand for self.server.browser."""
        return self.server.browser

    @property
    def tumblr(self):
        """Shorthand for self.server.tumblr."""
        return self.server.tumblr

    async def worker_loop(self):
        """Pick up items from the server's queue."""

        while True:
            task: RenderTask = await self.server.queue.get()

            t1 = time.time()
            try:
                ret = await task.run(worker=self)
            except:  # noqa: E722
                traceback.print_exc()
            t2 = time.time()
            print("Task execution time:", t2 - t1)

            self.server.results[task.task_id] = ret
            self.server.status[task.task_id].set()
            self.server.queue.task_done()


class Server:
    """Renderer server main object."""

    #: Browser to use for rendering.
    browser: Browser

    #: Tumblr API access object.
    tumblr: TumblrAPI

    #: Queue of posts to render.
    queue: asyncio.Queue[RenderTask]

    #: Workers created by the server.
    workers: list[Worker]

    #: Locks to indicate the status of each work.
    status: dict[str, asyncio.Event]

    #: Return values of each work.
    results: dict[str, Any]

    async def main_loop(self):
        """Perform renderer setup and run main loop."""

        self.browser = get_browser()
        self.tumblr = TumblrAPI(
            config.tumblr.consumer_key,
            config.tumblr.consumer_secret,
        )

        print("Starting browser...")
        await self.browser.start()
        print("Done, starting the server...")

        self.queue = asyncio.Queue()
        self.status = {}
        self.results = {}
        self.workers = []

        # Spawn workers
        for _ in range(config.render.worker_count):
            worker = Worker(server=self)
            worker.task = asyncio.create_task(worker.worker_loop())
            self.workers.append(worker)

        # Spawn server
        host = config.render.host
        port = int(config.render.port)
        server = await asyncio.start_server(self.handle_request, host, port)
        print(f"Render server listening @ {host}:{port}")
        async with server:
            await server.serve_forever()

    async def _handle_request(self, reader, writer):
        """Handle a request from the asyncio server."""
        data = await reader.read(1024)
        try:
            data = json.loads(data.decode())
        except (ValueError, json.decoder.JSONDecodeError):
            traceback.print_exc()
            print("Malformed render task:", data)
            writer.close()
            return

        try:
            task = RenderTask.from_dict(data)
        except ValueError:
            traceback.print_exc()
            print("Malformed render task:", data)
            writer.close()
            return

        # If we're not dealing with a duplicate task, add it to the queue
        if task.task_id not in self.status:
            self.status[task.task_id] = asyncio.Event()

            # Add the task to the queue
            await self.queue.put(task)

        # Wait for the task to complete
        await self.status[task.task_id].wait()

        # Get result and return it
        writer.write(self.results[task.task_id])
        await writer.drain()
        writer.close()

        # Delete the status event
        del self.status[task.task_id]

    async def handle_request(self, reader, writer):
        """
        Handle request.

        Wrapper for _handle_request which handles uncaught exceptions.
        """
        try:
            return await self._handle_request(reader, writer)
        except:  # noqa: E722
            print("Uncaught exception in task")
            traceback.print_exc()
            writer.close()

    async def on_close(self):
        """Clean up after the server."""
        for worker in self.workers:
            if worker.task:
                worker.task.cancel()

        await self.browser.close()
