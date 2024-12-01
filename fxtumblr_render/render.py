"""
Contains code for post rendering functionality. See README.md for more info.
"""

import asyncio
from inspect import getsourcefile
import jinja2
import os.path
import pyppeteer

from fxtumblr.config import config
from fxtumblr.npf import TumblrThread

from .paths import RENDERS_PATH, filename_for

# https://stackoverflow.com/questions/2632199/how-do-i-get-the-path-of-the-current-executed-file-in-python
FXTUMBLR_PATH = os.path.dirname(
    os.path.dirname(os.path.abspath(getsourcefile(lambda: 0)))
)

template_loader = jinja2.PackageLoader("fxtumblr_render")
template_env = jinja2.Environment(loader=template_loader, autoescape=True)
render_template = template_env.get_template("render.html")

browser = None


async def setup_browser() -> None:
    global browser
    if browser:
        try:
            await browser.close()
        except:  # noqa: E722
            pass
    browser = await pyppeteer.launch(
        executablePath=config.get("renders_chromium_path", "/usr/bin/chromium"),
        args=["--headless=old"] + config.get("renders_chromium_args", []),
        defaultViewport={"width": 540, "height": 100},
    )
    # keep alive by leaving blank page open
    await browser.newPage()


async def close_browser() -> None:
    global browser
    if browser:
        try:
            await browser.close()
        except:  # noqa: E722
            pass


async def render_thread(
    thread: TumblrThread, force_new_render: bool = False, modifiers: list = []
) -> bool:
    """
    Takes trail info from the generate_embed function and renders out
    the thread into a picture.
    """
    global browser

    if "unroll" in modifiers and not thread.unroll:
        thread.unroll = True

    target_filename = filename_for(thread.blog_name, thread.id, "png", modifiers)
    target_filename_html = filename_for(thread.blog_name, thread.id, "html", modifiers)
    target_html_path = os.path.join(RENDERS_PATH, target_filename_html)

    ret = True

    if (
        config.get("renders_debug", False)
        or force_new_render
        or f"{thread.blog_name}-{thread.id}" in config.get("renders_ignore_cache", [])
        or not os.path.exists(os.path.join(RENDERS_PATH, target_filename))
    ):
        rendered_html = render_template.render(
            thread=thread, fxtumblr_path=FXTUMBLR_PATH, modifiers=modifiers
        )
        with open(target_html_path, "w") as target_html:
            target_html.write(rendered_html)

        ret = False

        async def do_render(target_filename: str):
            ret = False

            page = await browser.newPage()
            try:
                async with asyncio.timeout(10):
                    await page.setViewport({"width": 540, "height": 100})
                    await page.goto(f"file://{target_html_path}")
                    await page.screenshot(
                        {
                            "path": os.path.join(RENDERS_PATH, target_filename),
                            "fullPage": True,
                            "omitBackground": True,
                        }
                    )
            except (TimeoutError, asyncio.exceptions.CancelledError):
                print(f"Timed out while rendering post: {thread.blog_name}-{thread.id}")

            await page.close()

            return ret

        try:
            ret = await do_render(target_filename)
            assert ret is True
        except:  # noqa: E722
            await close_browser()
            await setup_browser()
            ret = await do_render(target_filename)

    return ret
