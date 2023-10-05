"""
Contains code for creating the embed.
"""

import itertools
import pytumblr
from quart import request, render_template, redirect

from . import app
from .cache import post_needs_caching, cache_post, get_cached_post
from .config import APP_NAME, BASE_URL, config
from .render import render_thread
from .npf import TumblrThread

app.config["EXPLAIN_TEMPLATE_LOADING"] = False

tumblr = pytumblr.TumblrRestClient(
    config["tumblr_consumer_key"],
    config["tumblr_consumer_secret"],
    None,
    None,
)


@app.route("/<string:blogname>/<int:postid>")
@app.route("/<string:blogname>/<int:postid>/<string:summary>")
async def generate_embed(blogname: str, postid: int, summary: str = None):
    should_render = False
    needs_caching = post_needs_caching(blogname, postid)

    if needs_caching:
        _post = tumblr.posts(blogname=blogname, id=postid, reblog_info=True, npf=True)
        if not _post or "posts" not in _post or not _post["posts"]:
            return await parse_error(
                _post, post_url=f"https://www.tumblr.com/{blogname}/{postid}"
            )

        post = _post["posts"][0]
        needs_caching = cache_post(blogname, postid, _post)
    else:
        _post = get_cached_post(blogname, postid)
        post = _post["posts"][0]

    thread = TumblrThread.from_payload(post)
    thread_info = thread.thread_info

    # Get title and embed description (post content)
    title = thread_info.title
    try:
        pfp = _post["blog"]["avatar"][0]["url"]
    except (KeyError, IndexError):
        pfp = None

    # Get embed description
    description = ""
    for tpost in thread.posts:
        description += f"\n\n{tpost.blog_name}:\n" + tpost.to_markdown(
            placeholders=True
        )
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
        thread_info.images[0]._pick_one_size(target_width)["url"]

        if len(thread_info.images) > 1:
            should_render = True

    # Get video(s) for thread
    video = None
    if thread_info.videos:
        video = thread_info.videos[0][0].media[0]
        video_thumbnail = thread_info.videos[0][1].media[0]["url"]

        if len(thread_info.videos) > 1:
            should_render = True

        if "video" in request.args:
            return redirect(video["url"])

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

    reblog = {"by": "", "from": ""}
    try:
        reblog["from"] = post["reblogged_from_name"]
        reblog["by"] = post["blog_name"]
    except KeyError:
        pass

    op = thread.posts[0].blog_name
    miniheader = op + f' ({post["note_count"]} notes)'

    if reblog["from"]:
        header = reblog["by"] + " 🔁 " + reblog["from"]
    else:
        header = op

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
            description = f'TIP: You can get the raw video by pasting in the following link: {BASE_URL}/{post["blog_name"]}/{post["id"]}?video'
        else:
            description = ""
        video = None
    else:
        should_render = False

    return await render_template(
        "card.html",
        app_name=APP_NAME,
        base_url=BASE_URL,
        card_type=card_type,
        posturl=post["post_url"],
        image=image,
        pfp=pfp,
        video=video,
        video_thumbnail=video_thumbnail,
        header=header,
        miniheader=miniheader,
        op=op,
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

    return out
