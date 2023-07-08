"""
Contains code for post rendering functionality. See README.md for more info.
"""

from . import app
from .config import BASE_URL, config

browser = None

if config['renders_enable']:
    from quart import render_template, send_from_directory
    import tempfile
    import pyppeteer
    RENDERS_PATH = config['renders_path']

    # https://stackoverflow.com/questions/2632199/how-do-i-get-the-path-of-the-current-executed-file-in-python
    from inspect import getsourcefile
    import os.path
    FXTUMBLR_PATH = os.path.dirname(os.path.abspath(getsourcefile(lambda: 0)))

    @app.before_serving
    async def setup_browser():
        global browser
        if not browser:
            browser = await pyppeteer.launch()
            # keep alive by leaving blank page open
            await browser.newPage()

    @app.route('/renders/<path:path>')
    async def get_render(path):
        return await send_from_directory(RENDERS_PATH, path)

    async def render_thread(post: dict, trail: dict, reblog_info: dict = {}):
        """
        Takes trail info from the generate_embed function and renders out
        the thread into a picture. Returns a URL to the generated image.
        """
        global browser
        target_filename = f'{post["blog_name"]}-{post["id"]}.png'

        with tempfile.NamedTemporaryFile(suffix='.html') as target_html:
            target_html.write(bytes(await render_template('render.html',
                trail=trail, fxtumblr_path=FXTUMBLR_PATH, reblog_info=reblog_info),
                'utf-8'))

            page = await browser.newPage()
            await page.setViewport({'width': 560, 'height': 300})
            await page.goto(f'file://{target_html.name}')
            await page.screenshot(
                {'path': os.path.join(RENDERS_PATH, target_filename),
                 'fullPage': True, 'omitBackground': True}
            )
            await page.close()

        return BASE_URL + f'/renders/{target_filename}'
else:
    async def render_thread(*args, **kwargs):
        return False