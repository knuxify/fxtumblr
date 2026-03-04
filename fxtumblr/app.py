# SPDX-License-Identifier: MIT
"""Quart app entrypoint, setup and routes."""

import asyncio
import logging
import secrets
import traceback
from typing import Type

from quart import (
    Quart,
    Response,
    redirect,
    render_template,
    request,
    send_from_directory,
)

from . import config
from .embed.meta import MetaEmbed, MetaImageEmbed, MetaProfileEmbed, MetaVideoEmbed
from .post_embed import PostEmbed
from .render import RENDER_FILETYPE_MIMES, RenderFiletype
from .render.client import render_client
from .render.paths import (
    decode_legacy_filename,
    get_modifier_list,
    get_render_url,
)
from .stats import stats
from .tumblr import PrivateBlogException, TumblrAPI, TumblrAPIException

#: Main Quart application object.
app = Quart(__name__)
#: Main logger for the application.
logger = logging.getLogger(__name__)

# Template globals for use in Jinja templates.
app.jinja_env.globals["app_name"] = config.instance.name
app.jinja_env.globals["domain"] = config.instance.domain
app.jinja_env.globals["instance"] = {
    "name": config.instance.name,
    "contact_email": config.instance.contact_email,
}


#: Main Tumblr API instance.
tumblr = TumblrAPI(
    config.tumblr.consumer_key,
    config.tumblr.consumer_secret,
)


#: Whether or not statistics are enabled.
STATS_ENABLED: bool = config.stats.enabled


@app.route("/robots.txt")
async def robots_txt():
    """Provide the robots.txt file."""
    assert app.static_folder is not None
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

        if config.stats.password:

            async def _stats_auth():
                """Perform bearer token verification."""
                # The below assertion is never hit, as this function is only
                # defined/used when the password is not None; however mypy
                # doesn't realize that, so we specify it manually.
                assert config.stats.password is not None
                auth_header = request.headers.get("Authorization", "")
                if not auth_header.startswith("Bearer "):
                    return False
                token = auth_header[7:]
                return secrets.compare_digest(token, config.stats.password)

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
        post = await tumblr.get_post(blog_id, post_id, raise_on_private_blog=True)

    except PrivateBlogException:
        return await render_template(
            "locked.html", url=f"https://tumblr.com/{blog_id}/{post_id}"
        )

    except TumblrAPIException as e:
        logger.error(f"Failed to get post ({blog_id}-{post_id}) from API: {e}")
        traceback.print_exc()
        if STATS_ENABLED:
            await stats.increment_counter("error_count")
            await stats.increment_counter("api_error_count")
        return await render_template("error.html", msg="Failed to contact Tumblr."), 500

    except Exception as e:
        logger.error(f"Failed to parse post ({blog_id}-{post_id}): {e}")
        traceback.print_exc()
        if STATS_ENABLED:
            await stats.increment_counter("error_count")
            await stats.increment_counter("post_error_count")
        return await render_template(
            "error.html", msg="An error occured while parsing this post."
        ), 500

    if not post:
        return await render_template("error.html", msg="Post not found."), 404

    try:
        embed = PostEmbed.from_post(post)

    except Exception as e:
        logger.error(f"Failed to create embed for post ({blog_id}-{post_id}): {e}")
        traceback.print_exc()
        if STATS_ENABLED:
            await stats.increment_counter("error_count")
            await stats.increment_counter("embed_error_count")
        return await render_template(
            "error.html", msg="An error occured while embedding this post."
        ), 500

    _t = asyncio.create_task(stats.register_post_hit(blog_id, post_id))

    return await render_template("embed.html", post=post, embed=embed)


@app.route("/_api/oembed.json")
def api_oembed():
    """Generate oEmbed JSON from parameters."""

    embed_type = request.args.get("type")
    embed_class: Type[MetaEmbed]
    if embed_type == "photo":
        embed_class = MetaImageEmbed
    elif embed_type == "video":
        embed_class = MetaVideoEmbed
    elif embed_type == "profile":
        embed_class = MetaProfileEmbed
    else:
        embed_class = MetaEmbed

    params = dict(
        (k, v) for k, v in request.args.items() if k in embed_class.oembed_props
    )

    if "height" in params:
        params["height"] = int(params["height"])  # type: ignore[assignment]
    if "width" in params:
        params["width"] = int(params["width"])  # type: ignore[assignment]

    try:
        embed = embed_class(**params)
    except TypeError as e:
        return {"error": f"Unknown argument: {e}"}, 400
    return embed.to_oembed()


# Render routes


if config.render.redirect_legacy_urls:

    @app.route("/renders/<string:filename>")
    async def renders_legacy(filename: str):
        """Redirect legacy render URL to new URL."""
        try:
            blog_name, post_id, modifiers, filetype = decode_legacy_filename(filename)
        except ValueError as e:
            return {"error": str(e)}, 400

        return redirect(get_render_url(blog_name, post_id, modifiers, filetype))


@app.route(
    "/_api/renders/post/<string:blog_id>/<int:post_id>/render.<string:filetype_str>"
)
@app.route(
    "/_api/renders/post/<string:blog_id>/<int:post_id>/<string:modifiers_str>/render.<string:filetype_str>"
)
async def api_render_post(
    blog_id: str, post_id: int, filetype_str: str, modifiers_str: str | None = None
):
    """Get the cached post render or queue a new render."""

    try:
        filetype = RenderFiletype(filetype_str)
    except ValueError:
        return {"error": f"Unknown filetype {filetype_str}"}, 400

    if modifiers_str:
        try:
            modifiers = get_modifier_list(modifiers_str)
        except ValueError as e:
            return {"error": str(e)}, 400
    else:
        modifiers = []

    ret = await render_client.render_post(
        blog_id, post_id, modifiers, filetype, skip_cache="skip_cache" in request.args
    )

    # No return value: internal error
    if not ret:
        return {"error": "Internal render error"}, 500
    # Return value is JSON: error
    elif ret.startswith(b"{"):
        return ret, 400, {"Content-Type": "application/json"}
    # Otherwise, return the render
    return ret, 200, {"Content-Type": RENDER_FILETYPE_MIMES[filetype]}
