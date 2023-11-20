"""
Contains code for creating the embed.
"""

import logging
from quart import request, render_template, redirect

from . import app
from .cache import post_needs_caching
from .config import APP_NAME, BASE_URL, config
from .npf import TumblrThread
from .render import render_thread
from .tumblr import get_post

if config.get("logging", False):
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(name)s:%(levelname)s %(message)s"
    )


@app.route("/<string:blogname>/<int:postid>")
@app.route("/<string:blogname>/<int:postid>/<string:summary>")
async def generate_embed(blogname: str, postid: int, summary: str = None):
    app.logger.info(f"parsing post: https://www.tumblr.com/{blogname}/{postid}")

    should_render = False
    needs_caching = post_needs_caching(blogname, postid)
    post = get_post(blogname, postid)

    post_tumblr_url = f"https://www.tumblr.com/{blogname}/{postid}"
    if summary:
        post_tumblr_url += f"/{summary}"

    if "error" in post:
        return await parse_error(post, post_url=post_tumblr_url)

    unroll = False
    if "unroll" in request.args:
        unroll = True

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
    title = thread_info.title
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
        post_content = (
            "\n".join(l for l in post_content.split("\n") if l.strip())
        ).strip()
        if reblog["from"]:
            description += f"▪ {tpost.blog_name}:\n"
        description += post_content
    else:
        for tpost in tposts:
            post_content = tpost.to_markdown(placeholders=True)
            post_content = "\n".join(l for l in post_content.split("\n") if l.strip())
            description += f"\n\n▪ {tpost.blog_name}:\n" + post_content

    if post.get("is_submission", False):
        description += f"\n\n(Submitted by {post.get('post_author')}"

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
        image = thread_info.images[0]._pick_one_size(target_width)["url"]

        if len(thread_info.images) > 1:
            should_render = True

    # Get video(s) for thread
    video = None
    video_thumbnail = None
    if thread_info.videos:
        video = thread_info.videos[0][0].media[0]
        try:
            video_thumbnail = thread_info.videos[0][1].media[0]["url"]
        except (IndexError, AttributeError):
            video_thumbnail = None

        if len(thread_info.videos) > 1:
            should_render = True

        if "video" in request.args:
            return redirect(video["url"])

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

    if config["renders_enable"] and should_render:
        image = await render_thread(thread, force_new_render=needs_caching)
        card_type = "summary_large_image"
        if video:
            description = f'Hint: You can get the raw video by pasting in the following link: {BASE_URL}/{post["blog_name"]}/{post["id"]}?video'
        else:
            description = ""
        video = None
    else:
        should_render = False

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
        "type": request.args.get("ttype", None),
        "version": "1.0",
        "provider_name": "fxtumblr",
        "provider_url": "https://github.com/knuxify/fxtumblr",
        "title": request.args.get("op", None),
        "author_name": request.args.get("desc", None),
        "author_url": request.args.get("link", None),
    }

    if "motd" in config and config["motd"]:
        out["provider_name"] += " - " + config.get("motd", "")

    return out
