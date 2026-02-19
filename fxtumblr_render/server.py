# SPDX-License-Identifier: MIT
"""Main server loop and handling code."""

import asyncio
import json
import time
import traceback
from dataclasses import dataclass

from fxtumblr import config
from fxtumblr.tumblr import TumblrAPI

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
                await task.run(worker=self)
            except:  # noqa: E722
                traceback.print_exc()
            t2 = time.time()
            print("Task execution time:", t2 - t1)

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

    async def main_loop(self):
        """Perform renderer setup and run main loop."""

        self.browser = get_browser()
        self.tumblr = TumblrAPI(
            config["tumblr"]["consumer_key"],
            config["tumblr"]["consumer_secret"],
        )

        print("Starting browser...")
        await self.browser.start()
        print("Done, starting the server...")

        self.queue = asyncio.Queue()
        self.workers = []

        # Spawn workers
        for _ in range(config["render"].get("worker_count", 3)):
            worker = Worker(server=self)
            worker.task = asyncio.create_task(worker.worker_loop())
            self.workers.append(worker)

        # Spawn server
        host = config["render"].get("host", "localhost")
        port = int(config["render"].get("port", 6500))
        server = await asyncio.start_server(self.handle_request, host, port)
        print(f"Render server listening @ {host}:{port}")
        async with server:
            await server.serve_forever()

    async def handle_request(self, reader, writer):
        """Handle a request from the asyncio server."""
        data = await reader.read(1024)
        try:
            data = json.loads(data.decode())
        except (ValueError, json.decoder.JSONDecodeError):
            traceback.print_exc()
            print("Malformed render task:", data)
            return

        try:
            task = RenderTask.from_dict(data)
        except ValueError:
            traceback.print_exc()
            print("Malformed render task:", data)
            return

        self.queue.put_nowait(task)
        print("put task", task, "in queue")

    async def on_close(self):
        """Clean up after the server."""
        for worker in self.workers:
            if worker.task:
                worker.task.cancel()

        await self.browser.close()
