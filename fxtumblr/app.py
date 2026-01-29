# SPDX-License-Identifier: MIT
"""Quart app entrypoint, setup and routes."""

import asyncio
import logging
import secrets
import traceback

from quart import (
    Quart,
    Response,
    redirect,
    render_template,
    request,
    send_from_directory,
)

from . import config
from .embed import Embed, ImageEmbed, ProfileEmbed, VideoEmbed
from .stats import stats
from .tumblr import TumblrAPI

#: Main Quart application object.
app = Quart(__name__)
#: Main logger for the application.
logger = logging.getLogger(__name__)

# Template globals for use in Jinja templates.
app.jinja_env.globals["app_name"] = config["instance"].get("name", "fxtumblr")
app.jinja_env.globals["domain"] = config["instance"]["domain"]
app.jinja_env.globals["instance"] = {
    "name": config["instance"].get("name", "fxtumblr"),
    "contact_email": config["instance"]["contact_email"],
}


#: Main Tumblr API instance.
tumblr = TumblrAPI(
    config["tumblr"]["consumer_key"],
    config["tumblr"]["consumer_secret"],
)


#: Whether or not statistics are enabled.
STATS_ENABLED = config["stats"]["enabled"]


@app.route("/robots.txt")
async def robots_txt():
    """Provide the robots.txt file."""
    return await send_from_directory(app.static_folder, "robots.txt")


# Without the favicon in place, 404 requests from browsers get logged.
# This allows us to use Tumblr's favicon without bundling it in the repo.
@app.route("/favicon.ico")
async def favicon():
    """Provide the favicon."""
    return redirect("https://www.tumblr.com/favicon.ico")


@app.route("/")
async def index():
    """Render the index page."""
    return await render_template("index.html")


## Error handlers


@app.errorhandler(404)
async def handle_404(e):
    """Handle 404 error."""
    return await render_template("error.html", msg="This page could not be found."), 404


@app.errorhandler(500)
async def handle_500(e):
    """Handle 500 error."""
    return await render_template(
        "error.html", msg="An internal server error has occured."
    ), 500


## Statistics


if STATS_ENABLED:

    @app.route("/_stats")
    async def stats_route():
        """Get the Prometheus stats for this instance."""

        if config["stats"].get("password"):

            async def _stats_auth():
                """Perform bearer token verification."""
                auth_header = request.headers.get("Authorization", "")
                if not auth_header.startswith("Bearer "):
                    return False
                token = auth_header[7:]
                return secrets.compare_digest(token, config["stats"]["password"])

            if not await _stats_auth():
                return Response(
                    "Unauthorized",
                    status=401,
                    headers={"WWW-Authenticate": 'Bearer realm="Metrics"'},
                )

        else:
            logger.warning(
                "Stats endpoint without password; this is insecure and should not be used in production."
            )

        return Response(
            await stats.generate_prometheus_metrics(),
            mimetype="text/plain; version=1.0.0; charset=utf-8",
        )


## Embed generation endpoint


@app.route("/<string:blog_id>/<int:post_id>")
@app.route("/<string:blog_id>/<int:post_id>/")
@app.route("/<string:blog_id>/<int:post_id>/<string:summary>")
@app.route("/<string:blog_id>/<int:post_id>/<string:summary>/")
async def generate_embed(blog_id: str, post_id: int, summary: str | None = None):
    """Embed generation endpoint."""

    try:
        post = await tumblr.get_post(blog_id, post_id)
    except Exception as e:
        logger.error(f"Failed to get post ({blog_id}-{post_id}): {e}")
        traceback.print_exc()
        if STATS_ENABLED:
            await stats.increment_counter("error_counter")
            await stats.increment_counter("post_error_counter")

    if not post:
        return await render_template("error.html", msg="Post not found."), 404

    try:
        embed = Embed.from_post(post)
    except Exception as e:
        logger.error(f"Failed to create embed for post ({blog_id}-{post_id}): {e}")
        traceback.print_exc()
        if STATS_ENABLED:
            await stats.increment_counter("error_counter")
            await stats.increment_counter("embed_error_counter")

    _t = asyncio.create_task(stats.register_post_hit(blog_id, post_id))

    return await render_template("embed.html", post=post, embed=embed)


@app.route("/_api/oembed.json")
def api_oembed():
    """Generate oEmbed JSON from parameters."""

    embed_type = request.args.get("type")
    if embed_type == "image":
        embed_class = ImageEmbed
    elif embed_type == "video":
        embed_class = VideoEmbed
    elif embed_type == "profile":
        embed_class = ProfileEmbed
    else:
        embed_class = Embed

    params = dict(
        (k, v) for k, v in request.args.items() if k in embed_class.oembed_props
    )

    if "height" in params:
        params["height"] = int(params["height"])
    if "width" in params:
        params["width"] = int(params["width"])

    try:
        embed = embed_class(**params)
    except TypeError as e:
        return {"error": f"Unknown argument: {e}"}, 500
    return embed.to_oembed()
