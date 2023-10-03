"""
fxtumblr - fix Tumblr embeds on other websites
inspired by, and borrowing some code from the original TwitFix:
https://github.com/robinuniverse/TwitFix/

(c) knuxify 2023, https://github.com/knuxify/fxtumblr
"""
from quart import Quart, redirect
from quart_cors import cors
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from .config import config

# Initial setup to get things up and running
app = Quart(__name__)  # Quart app
app.asgi_app = ProxyHeadersMiddleware(app.asgi_app, trusted_hosts=["127.0.0.1"])
cors(app)

from . import embeds  # noqa: F401,E402

if config["renders_enable"]:
    from . import render  # noqa: F401


@app.route("/")
async def redirect_to_repo():
    return redirect("https://github.com/knuxify/fxtumblr")
