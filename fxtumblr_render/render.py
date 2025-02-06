"""
Contains code for post rendering functionality. See README.md for more info.
"""

import asyncio
from inspect import getsourcefile
import jinja2
import os.path

from fxtumblr.config import config
from fxtumblr.npf import TumblrThread

from .paths import RENDERS_PATH, filename_for

BROWSER_TYPE = config.get("renders_browser", "pyppeteer")
if BROWSER_TYPE == "pyppeteer":
    import pyppeteer
elif BROWSER_TYPE.startswith("playwright"):
    import playwright.async_api
else:
    raise ValueError("Invalid value for renders_browser config option; must be one of pyppeteer, playwright-chromium, playwright-firefox, playwright-webkit")

# https://stackoverflow.com/questions/2632199/how-do-i-get-the-path-of-the-current-executed-file-in-python
FXTUMBLR_PATH = os.path.dirname(
    os.path.dirname(os.path.abspath(getsourcefile(lambda: 0)))
)

template_loader = jinja2.PackageLoader("fxtumblr_render")
template_env = jinja2.Environment(loader=template_loader, autoescape=True)
render_template = template_env.get_template("render.html")

browser = None
playwright_async = None

async def setup_browser() -> None:
    global browser
    global playwright_async

    await close_browser()

    if BROWSER_TYPE == "pyppeteer":
        browser = await pyppeteer.launch(
            executablePath=config.get("renders_chromium_path", "/usr/bin/chromium"),
            args=["--headless=old"] + config.get("renders_chromium_args", []),
            defaultViewport={"width": 540, "height": 100},
        )
        # keep alive by leaving blank page open
        await browser.newPage()

    elif BROWSER_TYPE.startswith("playwright"):
        playwright_async = await playwright.async_api.async_playwright().start()

        if BROWSER_TYPE == "playwright-chromium":
            browser_type = playwright_async.chromium
            browser = await browser_type.launch(executable_path=config.get("renders_chromium_path", None))
        elif BROWSER_TYPE == "playwright-firefox":
            browser_type = playwright_async.firefox
            browser = await browser_type.launch()
        elif BROWSER_TYPE == "playwright-webkit":
            browser_type = playwright_async.webkit
            browser = await browser_type.launch()
        else:
            raise ValueError("Incorrect playwright browser type; must be one of playwright-{chromium,firefox,webkit}")



async def close_browser() -> None:
    global browser
    global playwright_async
    if browser:
        try:
            await browser.close()
        except:  # noqa: E722
            pass
    if playwright_async:
        try:
            await playwright_async.close()
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

        if BROWSER_TYPE == "pyppeteer":
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
                except:
                    traceback.print_exc()
                    ret = False
                else:
                    ret = True

                await page.close()

                return ret

        elif BROWSER_TYPE.startswith("playwright"):
            async def do_render(target_filename: str):
                ret = False

                page = await browser.new_page()
                try:
                    async with asyncio.timeout(10):
                        await page.set_viewport_size({"width": 540, "height": 100})
                        await page.goto(f"file://{target_html_path}")
                        await page.screenshot(
                            path=os.path.join(RENDERS_PATH, target_filename),
                            full_page=True,
                            omit_background=True
                        )
                except (TimeoutError, asyncio.exceptions.CancelledError):
                    print(f"Timed out while rendering post: {thread.blog_name}-{thread.id}")
                except:
                    traceback.print_exc()
                    ret = False
                else:
                    ret = True

                await page.close()

                return ret

        else:
            raise ValueError("Invalid browser type")

        try:
            ret = await do_render(target_filename)
            assert ret is True
        except:  # noqa: E722
            await setup_browser()
            ret = await do_render(target_filename)

    return ret
