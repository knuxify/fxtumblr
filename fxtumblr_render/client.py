import asyncio
import json
import traceback
import os.path

from fxtumblr.config import config
from .paths import path_to

_queue = set()


async def render_thread(blogname: str, post_id: int, modifiers: list = []) -> bool:
    global _queue

    reader, writer = await asyncio.open_connection(
        config.get("renders_host", "localhost"), int(config.get("renders_port", 6500))
    )

    work_id = f"{blogname}-{post_id}"
    if modifiers:
        work_id += f"-{','.join(sorted(modifiers))}"
    if work_id not in _queue:
        _queue.add(work_id)

        to_send = {
            "blogname": blogname,
            "post_id": post_id,
            "modifiers": modifiers,
            "work_id": work_id,
        }

        try:
            writer.write(bytes(json.dumps(to_send), "utf-8"))
            await writer.drain()
        except:
            print("Error on render sendoff!")
            traceback.print_exc()
            _queue.remove(work_id)
            return False

        while True:
            data = await reader.read(1024)
            try:
                data = json.loads(data.decode())
                if data["work_id"] == work_id:
                    break
            except (ValueError, KeyError, json.decoder.JSONDecodeError):
                traceback.print_exc()
                continue

        _queue.remove(work_id)
    else:
        while True:
            await asyncio.sleep(0.5)
            if work_id not in _queue:
                break
        data = {
            "work_id": work_id,
            "return": os.path.exists(
                path_to(blogname, post_id, extension="png", modifiers=modifiers)
            ),
        }

    response = data.get("return", False)

    writer.close()
    await writer.wait_closed()

    return response
