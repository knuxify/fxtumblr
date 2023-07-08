"""
fxtumblr - fix Tumblr embeds on other websites
inspired by, and borrowing some code from the original TwitFix:
https://github.com/robinuniverse/TwitFix/

(c) knuxify 2023, https://github.com/knuxify/fxtumblr
"""

from quart import Quart, redirect
from quart_cors import cors
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import BASE_URL, config

# Initial setup to get things up and running
app = Quart(__name__)  # Quart app
cors(app)

if '127.0.0.1' not in BASE_URL:
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

from . import embeds  # noqa: F401
if config['renders_enable']:
    from . import render  # noqa: F401


@app.route('/')
async def redirect_to_repo():
    return redirect('https://github.com/knuxify/fxtumblr')
