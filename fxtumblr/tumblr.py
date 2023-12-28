"""
Contains code for getting posts.
"""

import pytumblr

from .cache import (
    post_needs_caching,
    cache_post,
    get_cached_post,
    poll_needs_caching,
    cache_poll,
    get_cached_poll,
    cache_avatar,
    get_cached_avatar,
    avatar_needs_caching,
)
from .config import config

tumblr = pytumblr.TumblrRestClient(
    config["tumblr_consumer_key"],
    config["tumblr_consumer_secret"],
    None,
    None,
)


def get_post(blogname: str, postid: str):
    needs_caching = post_needs_caching(blogname, postid)
    post = None

    if needs_caching:
        _post = tumblr.posts(blogname=blogname, id=postid, reblog_info=True, npf=True)
        if not _post or "posts" not in _post or not _post["posts"]:
            if "error" not in _post:
                _post["error"] = True
            return _post

        try:
            blogname = _post["blog"]["name"]
        except KeyError:
            blogname = _post["broken_blog_name"]

        post = _post["posts"][0]
        cache_post(blogname, postid, _post)
    else:
        _post = get_cached_post(blogname, postid)
        post = _post["posts"][0]
    if "blog" in _post:
        post["_fx_author_blog"] = _post["blog"]

    return post


def get_poll(blog_name: str, post_id: str, poll_id: str, block: dict):
    """Gets data about a poll from Tumblr's API. Note that this API is undocumented and subject to change; it's also missing most of the useful information, so we need to merge it with the block data."""
    needs_caching = poll_needs_caching(blog_name, int(post_id), poll_id)

    poll = None

    if needs_caching:
        try:
            poll = tumblr.send_api_request(
                "get", f"/v2/polls/{blog_name}/{post_id}/{poll_id}/results"
            )
            assert "error" not in poll
        except:
            return None

        poll = poll | block
        cache_poll(blog_name, post_id, poll)
    else:
        poll = get_cached_poll(blog_name, post_id, poll_id)

    return poll


def get_avatar(blog_name: str):
    """Gets the URL of the avatar for the post from Tumblr's API."""
    needs_caching = avatar_needs_caching(blog_name)

    avatar_url = None
    if needs_caching:
        avatar_data = tumblr.avatar(blog_name)
        if "avatar_url" in avatar_data:
            avatar_url = avatar_data["avatar_url"]
        cache_avatar(blog_name, avatar_url)
    else:
        avatar_url = get_cached_avatar(blog_name)

    return avatar_url
