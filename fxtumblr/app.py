from quart import Quart, redirect, send_from_directory
from quart_cors import cors
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from .config import config

# Initial setup to get things up and running
app = Quart(__name__)  # Quart app
app.config["EXPLAIN_TEMPLATE_LOADING"] = False  # workaround for jinja flask dependency?
app.asgi_app = ProxyHeadersMiddleware(app.asgi_app, trusted_hosts=["127.0.0.1"])
cors(app)


@app.route("/robots.txt")
async def robots_txt():
    return await send_from_directory(app.static_folder, "robots.txt")


from . import embeds  # noqa: F401,E402

if config["renders_enable"]:
    from . import renders  # noqa: F401


@app.route("/")
async def redirect_to_repo():
    return redirect("https://github.com/knuxify/fxtumblr")
