import asyncio
import json
import traceback
from contextlib import suppress

from fxtumblr.config import config
from fxtumblr.tumblr import get_post
from fxtumblr.npf import TumblrThread

from .render import setup_browser, close_browser, render_thread

LOG_ENABLED = config.get("logging", False)

class RenderServer:
    async def main_loop(self):
        """Main loop for the renderer."""
        await setup_browser()

        self.queue = asyncio.Queue()
        self.workers = []
        for i in range(int(config.get("renders_workers", 3))):
            w = asyncio.create_task(self.worker(f"worker-{i}"))
            self.workers.append(w)

        server = await asyncio.start_server(
            self.handle_request,
            config.get("renders_host", "localhost"),
            int(config.get("renders_port", 6500)),
        )
        print("Render server ready.")
        async with server:
            await server.serve_forever()

    async def on_exit(self):
        print("Exiting...")
        try:
            for w in self.workers:
                w.cancel()
                with suppress(asyncio.CancelledError):
                    await w

            await self.queue.join()
        except AttributeError:
            pass
        await close_browser()

    async def handle_request(self, reader, writer):
        data = await reader.read(1024)
        try:
            data = json.loads(data.decode())
        except (ValueError, json.decoder.JSONDecodeError):
            return

        self.queue.put_nowait(
            (
                writer,
                data["blogname"],
                data["post_id"],
                data["modifiers"],
                data["work_id"],
            )
        )

    async def worker(self, name):
        while True:
            writer, blogname, post_id, modifiers, work_id = await self.queue.get()
            ret = False

            if LOG_ENABLED:
                print(f"[{name}] Rendering post {blogname}-{post_id} with modifiers {modifiers} (work ID: {work_id})")

            try:
                post = get_post(blogname, post_id)
                if not post:
                    raise ValueError
                elif "errors" in post and post["errors"]:
                    raise ValueError("Post has error:", post)
                thread = TumblrThread.from_payload(post, unroll=("unroll" in modifiers))
            except:  # noqa: E722
                print(
                    f"[{name}] Exception while fetching {blogname}-{post_id} with modifiers {modifiers} (work ID: {work_id}):"
                )
                traceback.print_exc()
            else:
                async with asyncio.timeout(
                    11
                ):  # slightly longer than render_thread timeout
                    try:
                        ret = await render_thread(thread, modifiers=modifiers)
                    except:  # noqa: E722
                        print(
                            f"[{name}] Exception while rendering {blogname}-{post_id} with modifiers {modifiers} (work ID: {work_id}):"
                        )
                        traceback.print_exc()

            if LOG_ENABLED:
                print(
                    f"[{name}] Result for {blogname}-{post_id} with modifiers {modifiers} (work ID: {work_id}): {ret}"
                )

            writer.write(
                bytes(json.dumps({"work_id": work_id, "return": ret}), "utf-8")
            )
            await writer.drain()
            writer.close()
            self.queue.task_done()
