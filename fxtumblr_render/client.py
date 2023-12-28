import asyncio
import json
from uuid import uuid4
import traceback

from fxtumblr.config import config


async def render_thread(blogname: str, post_id: int, modifiers: list = []) -> bool:
    reader, writer = await asyncio.open_connection(
        config.get("renders_host", "localhost"), int(config.get("renders_port", 6500))
    )

    work_id = str(uuid4())
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
        traceback.print_exc()
        self.disconnect()
        self.connect()
        try:
            writer.write(bytes(json.dumps(to_send), "utf-8"))
            await writer.drain()
        except:
            print("Error on render sendoff!")
            traceback.print_exc()
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

    response = data.get("return", False)

    writer.close()
    await writer.wait_closed()

    return response
