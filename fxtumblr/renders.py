from .app import app
from .config import BASE_URL, config
import fxtumblr_render.paths
from fxtumblr_render.client import render_thread
import os.path
import asyncio

from quart import render_template, send_from_directory

RENDERS_PATH = config["renders_path"]


@app.route("/renders/<filename>")
async def get_render(filename: str):
    if not config.get("renders_enable", False):
        return "", 404

    try:
        filename = fxtumblr_render.paths.normalize_filename(filename)
    except ValueError:
        return "", 404
    path = os.path.join(RENDERS_PATH, filename)
    path_split = fxtumblr_render.paths.from_filename(filename)

    if (
        not os.path.exists(path)
        or config.get("renders_debug", False)
        or path_split["blogname"] + "-" + str(path_split["post_id"])
        in config.get("renders_ignore_cache", [])
    ):
        render_succeeded = False
        try:
            async with asyncio.timeout(12):  # slightly longer than renderer itself
                render_succeeded = await render_thread(
                    path_split["blogname"],
                    path_split["post_id"],
                    path_split["modifiers"],
                )
        except TimeoutError:
            render_succeeded = False

        if not render_succeeded:
            return "", 404

    return await send_from_directory(RENDERS_PATH, filename)
