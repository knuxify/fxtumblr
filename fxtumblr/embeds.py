"""
Contains code for creating the embed.
"""

import asyncio
import logging
import traceback
import re
from quart import request, render_template, redirect
import os.path

from .app import app
from .cache import post_needs_caching
from .config import APP_NAME, BASE_URL, config
from .stats import register_hit
from .npf import TumblrThread

from fxtumblr_render.paths import filename_for, path_to

from .tumblr import get_post

LOG_ENABLED = config.get("logging", False)
STATS_ENABLED = config.get("statistics", False)

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(name)s:%(levelname)s %(message)s"
)

stats_tasks = set()


@app.route("/<string:blogname>/<int:postid>")
@app.route("/<string:blogname>/<int:postid>/<string:summary>")
async def generate_embed_route(blogname: str, postid: int, summary: str = None):
    global stats_tasks

    if LOG_ENABLED:
        app.logger.info(f"parsing post: https://www.tumblr.com/{blogname}/{postid}")

    if STATS_ENABLED:
        modifiers = []
        for mod in ("unroll", "dark"):
            if mod in request.args:
                modifiers.append(mod)

    try:
        ret = await generate_embed(blogname, postid, summary)
    except:
        app.logger.info(
            f"Failed to parse post https://www.tumblr.com/{blogname}/{postid}:"
        )
        traceback.print_exc()
        if STATS_ENABLED:
            task = asyncio.create_task(
                register_hit(blogname, postid, modifiers, failed=True)
            )
            stats_tasks.add(task)
            task.add_done_callback(stats_tasks.discard)
    else:
        if STATS_ENABLED:
            task = asyncio.create_task(
                register_hit(blogname, postid, modifiers, failed=False)
            )
            stats_tasks.add(task)
            task.add_done_callback(stats_tasks.discard)
        return ret


async def generate_embed(blogname: str, postid: int, summary: str = None):
    should_render = False
    needs_caching = post_needs_caching(blogname, postid)
    post = get_post(blogname, postid)

    post_tumblr_url = f"https://www.tumblr.com/{blogname}/{postid}"
    if summary:
        post_tumblr_url += f"/{summary}"

    if "error" in post:
        app.logger.info(f"error while parsing post: https://www.tumblr.com/{blogname}/{postid}")
        app.logger.info(post)
        return await parse_error(post, post_url=post_tumblr_url)

    unroll = False
    if "unroll" in request.args:
        unroll = True

    dark = False
    if "dark" in request.args:
        dark = True

    thread = TumblrThread.from_payload(post, unroll=unroll)
    thread_info = thread.thread_info

    # Get reblog information
    reblog = {
        "by": post.get(
            "blog_name", post["blog"].get("name", post["blog"].get("broken_blog_name"))
        ),
        "from": post.get("reblogged_from_name"),
    }

    # Get title and embed description (post content)
    try:
        pfp = post["_fx_author_blog"]["avatar"][0]["url"]
    except (KeyError, IndexError):
        pfp = None

    # Get embed description
    description = ""

    # Reblogs show up as empty posts in the thread so we have to ignore them
    tposts = [p for p in thread.posts if p.to_markdown(placeholders=True).strip()]
    if len(tposts) == 1:
        tpost = tposts[0]
        post_content = tpost.to_markdown(
            placeholders=True, skip_single_placeholders=True
        )
        post_content = re.sub("^(\n)+", "\n", post_content)
        if reblog["from"]:
            description += f"▪ {tpost.blog_name}:\n"
        description += post_content.strip()
    else:
        for tpost in tposts:
            post_content = tpost.to_markdown(placeholders=True)
            post_content = re.sub("^(\n)+", "\n", post_content)
            description += f"\n\n▪ {tpost.blog_name}:\n" + post_content.strip()

    if post.get("is_submission", False):
        description += f"\n\n(Submitted by {post.get('post_author')})"

    if "tags" in post and post["tags"]:
        description += "\n\n(#" + " #".join(post["tags"]) + ")"
    description = description.strip()

    # Get image(s) for thread
    image = None
    if thread_info.images:
        if thread_info.images[0].original_dimensions:
            target_width = thread_info.images[0].original_dimensions[0]
        else:
            target_width = 640  # pick whatever
        image = thread_info.images[0]._pick_one_size(target_width)

        if len(thread_info.images) > 1:
            should_render = True

    # Get video(s) for thread
    video = None
    video_thumbnail = None
    if thread_info.videos:
        if len(thread_info.videos) > 1:
            should_render = True

        try:
            video = thread_info.videos[0][0].media[0]
        except (IndexError, AttributeError):
            # This usually happens when the video is an embed, in which case,
            # we wanna render instead
            should_render = True
        else:
            if "video" in request.args:
                return redirect(video["url"])

            try:
                video_thumbnail = thread_info.videos[0][1].media[0]["url"]
            except (IndexError, AttributeError):
                video_thumbnail = None

    # Get audio for thread
    if thread_info.audio:
        if "audio" in request.args:
            return redirect(thread_info.audio[0][0].media[0]["url"])

    # Truncate description (a maximum of 349 characters can be displayed, 256 for video desc)
    if video:
        truncate_placeholder = "... (click to see full thread)"
        max_desc_length = 256 - len(truncate_placeholder)
    else:
        truncate_placeholder = "... (see full thread)"
        max_desc_length = 349 - len(truncate_placeholder)

    if len(description) > max_desc_length:
        description = description[:max_desc_length] + truncate_placeholder
        should_render = True

    miniheader = f'{post["note_count"]} notes'

    if reblog["by"] and reblog["from"]:
        if reblog["by"] == reblog["from"]:
            header = reblog["by"] + " 🔁"
        else:
            header = reblog["by"] + " 🔁 " + reblog["from"]
    else:
        header = reblog[
            "by"
        ]  # this actually contains the op's blog name if there's no reblog

    if image and video:
        should_render = True

    if thread_info.audio or thread_info.other_blocks:
        should_render = True

    if thread_info.has_formatting:
        should_render = True

    card_type = "tweet"
    if image and not video:
        card_type = "summary_large_image"
    elif video and not image:
        card_type = "video"

    modifiers = []

    if config["renders_enable"] and should_render:
        description = ""
        if unroll:
            modifiers.append("unroll")
        if dark:
            modifiers.append("dark")
        render_path = (
            BASE_URL
            + "/renders/"
            + filename_for(blogname, postid, extension="png", modifiers=modifiers)
        )
        image = {"url": render_path, "width": 0, "height": 0}
        card_type = "summary_large_image"
        if video:
            description = f'(Hint: You can get the raw video by pasting in the following link: {BASE_URL}/{post["blog_name"]}/{post["id"]}?video)'

        video = None
    else:
        should_render = False

    if LOG_ENABLED:
        app.logger.info(f"parsed post {blogname}/{postid}, rendered: {should_render}")

    return await render_template(
        "card.html",
        app_name=APP_NAME,
        base_url=BASE_URL,
        motd=config.get("motd", ""),
        card_type=card_type,
        posturl=post_tumblr_url,
        image=image,
        pfp=pfp,
        video=video,
        video_thumbnail=video_thumbnail,
        header=header,
        miniheader=miniheader,
        op=reblog["by"],
        desc=description,
        is_rendered=should_render,
    )


async def parse_error(info: dict, post_url: str = None):
    """Parses error returned by Tumblr API."""
    app.logger.error(f"Error while parsing post {post_url}:")
    app.logger.error(info)

    if not info or "meta" not in info:
        return (
            await render_template(
                "error.html", app_name=APP_NAME, msg="Internal server error."
            ),
            500,
        )

    if info["meta"]["status"] == 404:
        if "errors" in info and info["errors"] and info["errors"][0]["code"] == 4012:
            return await render_template(
                "locked.html", app_name=APP_NAME, posturl=post_url
            )
        return (
            await render_template(
                "error.html", app_name=APP_NAME, msg="Post not found."
            ),
            404,
        )

    return (
        await render_template(
            "error.html", app_name=APP_NAME, msg="Internal server error."
        ),
        500,
    )


@app.route("/oembed.json")
async def oembed_json():
    out = {
        "type": request.args.get("type", "link"),
        "version": "1.0",
        "provider_name": "fxtumblr",
        "provider_url": config.get("motd_url", "https://github.com/knuxify/fxtumblr"),
        "title": request.args.get("title", None),
        "author_name": request.args.get("author_name", None),
        "author_url": request.args.get("author_url", None),
    }

    for prop in ("url", "width", "height"):
        if prop in request.args:
            out[prop] = request.args[prop]

    if "motd" in config and config["motd"]:
        out["provider_name"] += " - " + config.get("motd", "")

    return out

# Without the favicon in place, 404 requests from browsers get logged.
# This allows us to use Tumblr's favicon without bundling it in the repo.
@app.route("/favicon.ico")
async def favicon():
    return redirect("https://www.tumblr.com/favicon.ico")
