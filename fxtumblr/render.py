"""
Contains code for post rendering functionality. See README.md for more info.
"""

from . import app
from .config import BASE_URL, config
from .npf import TumblrThread
from .tumblr import get_post
import shutil
import time

browser = None
playwright_async = None

if config["renders_enable"]:
    from quart import render_template, send_from_directory
    import tempfile
    import playwright.async_api

    RENDERS_PATH = config["renders_path"]

    # https://stackoverflow.com/questions/2632199/how-do-i-get-the-path-of-the-current-executed-file-in-python
    from inspect import getsourcefile
    import os.path

    FXTUMBLR_PATH = os.path.dirname(
        os.path.dirname(os.path.abspath(getsourcefile(lambda: 0)))
    )

    @app.before_serving
    async def setup_browser():
        global browser
        global playwright_async

        if not browser:
            playwright_async = await playwright.async_api.async_playwright().start()

            browser_type_str = config.get('render_browser', 'chromium')
            if browser_type_str == 'chromium':
                browser_type = playwright_async.chromium
            elif browser_type_str == 'firefox':
                browser_type = playwright_async.firefox
            elif browser_type_str == 'webkit':
                browser_type = playwright_async.chromium
            else:
                raise ValueError("Incorrect browser type; must be one of chromium, firefox, webkit")

            browser = await browser_type.launch()

    @app.after_serving
    async def destroy_browser():
        global browser
        global playwright_async
        browser.close()
        playwright_async.close()

    @app.route("/renders/<blogname>-<postid>.png")
    @app.route("/renders/<blogname>-<postid>.<suffix>.png")
    async def get_render(blogname, postid, suffix=False):
        unroll = True if suffix == "unroll" else False
        if unroll:
            target_filename = f"{blogname}-{postid}.unroll.png"
        else:
            target_filename = f"{blogname}-{postid}.png"

        if (
            not os.path.exists(os.path.join(RENDERS_PATH, target_filename))
            or config["renders_debug"]
        ):
            post = get_post(blogname, postid)
            if "error" in post:
                return "", 404
            thread = TumblrThread.from_payload(post, unroll=unroll)
            await render_thread(thread)
        return await send_from_directory(RENDERS_PATH, target_filename)

    @app.route("/renders/<blogname>-<postid>.html")
    @app.route("/renders/<blogname>-<postid>.<suffix>.html")
    async def get_html_render(blogname, postid, suffix=False):
        unroll = True if suffix == "unroll" else False
        if unroll:
            target_filename = f"{blogname}-{postid}.unroll.html"
        else:
            target_filename = f"{blogname}-{postid}.html"

        if (
            not os.path.exists(os.path.join(RENDERS_PATH, target_filename))
            or config["renders_debug"]
        ):
            post = get_post(blogname, postid)
            if "error" in post:
                return "", 404
            thread = TumblrThread.from_payload(post, unroll=unroll)
            await render_thread(thread)
        return await send_from_directory(RENDERS_PATH, target_filename)

    async def render_thread(thread: TumblrThread, force_new_render: bool = False):
        """
        Takes trail info from the generate_embed function and renders out
        the thread into a picture. Returns a URL to the generated image.
        """
        global browser
        unroll = thread.unroll
        if unroll:
            target_filename = f"{thread.blog_name}-{thread.id}.unroll.png"
            target_filename_html = f"{thread.blog_name}-{thread.id}.unroll.html"
        else:
            target_filename = f"{thread.blog_name}-{thread.id}.png"
            target_filename_html = f"{thread.blog_name}-{thread.id}.html"

        if (
            config["renders_debug"]
            or force_new_render
            or not os.path.exists(os.path.join(RENDERS_PATH, target_filename))
        ):
            with tempfile.NamedTemporaryFile(suffix=".html") as target_html:
                target_html.write(
                    bytes(
                        await render_template(
                            "render.html", thread=thread, fxtumblr_path=FXTUMBLR_PATH
                        ),
                        "utf-8",
                    )
                )

                if config["renders_debug"]:
                    shutil.copyfile(target_html.name, "latest-render.html")

                shutil.copyfile(
                    target_html.name,
                    os.path.join(RENDERS_PATH, target_filename_html),
                )

                page = await browser.new_page()
                await page.set_viewport_size({"width": 540, "height": 100})
                await page.goto(f"file://{target_html.name}")
                await page.screenshot(
                    path=os.path.join(RENDERS_PATH, target_filename),
                    full_page=True,
                    omit_background=True,
                )
                await page.close()

        return BASE_URL + f"/renders/{target_filename}"

else:

    async def render_thread(*args, **kwargs):
        return False
