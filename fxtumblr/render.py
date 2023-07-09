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

    async def render_thread(post: dict, trail: dict, reblog_info: dict = {},
                            force_new_render: bool = False):
        """
        Takes trail info from the generate_embed function and renders out
        the thread into a picture. Returns a URL to the generated image.
        """
        global browser
        target_filename = f'{post["blog_name"]}-{post["id"]}.png'

        if 'by' not in reblog_info or 'from' not in reblog_info or \
                not reblog_info['by'] or not reblog_info['from']:
            reblog_info = None

        if force_new_render or not os.path.exists(os.path.join(RENDERS_PATH, target_filename)):
            with tempfile.NamedTemporaryFile(suffix='.html') as target_html:
                target_html.write(bytes(await render_template('render.html',
                    trail=trail, fxtumblr_path=FXTUMBLR_PATH,
                    reblog_info=reblog_info, tags=post['tags']),
                    'utf-8'))

                page = await browser.newPage()
                await page.setViewport({'width': 560, 'height': 300})
                await page.goto(f'file://{target_html.name}')
                height = await page.evaluate('document.body.scrollHeight')
                await page.screenshot(
                    {'path': os.path.join(RENDERS_PATH, target_filename),
                     'fullPage': True, 'omitBackground': True}
                )
                await page.close()

        return (BASE_URL + f'/renders/{target_filename}', 560, height)
else:
    async def render_thread(*args, **kwargs):
        return False
