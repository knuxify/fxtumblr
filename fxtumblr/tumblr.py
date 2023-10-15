"""
Contains code for getting posts.
"""

import pytumblr

from .cache import post_needs_caching, cache_post, get_cached_post
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
        if blogname == "post":
            _post = tumblr.posts(id=postid, reblog_info=True, npf=True)
        else:
            _post = tumblr.posts(
                blogname=blogname, id=postid, reblog_info=True, npf=True
            )
        if not _post or "posts" not in _post or not _post["posts"]:
            if "error" not in _post:
                _post["error"] = True
            return _post

        try:
            blogname = _post["blog"]["name"]
        except KeyError:
            blogname = _post["broken_blog_name"]

        post = _post["posts"][0]
        needs_caching = cache_post(blogname, postid, _post)
    else:
        _post = get_cached_post(blogname, postid)
        post = _post["posts"][0]

    return post
