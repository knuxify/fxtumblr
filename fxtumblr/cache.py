"""
Contains code for managing the cache.
"""

import json
import os.path
import time
import datetime
import dateutil

from .config import config

cache: dict = {"posts": {}, "polls": {}}
if os.path.exists(config["cache_path"]):
    with open(config["cache_path"]) as cache_file:
        cache = json.load(cache_file)


def save_cache():
    with open(config["cache_path"], "w+") as cache_file:
        json.dump(cache, cache_file)


def post_needs_caching(blogname, postid) -> bool:
    if f"{blogname}-{postid}" not in cache["posts"]:
        return True
    if (
        time.time() - cache["posts"][f"{blogname}-{postid}"]["cache_time"]
        >= config["cache_expiry"]
    ):
        return True
    return False


def cache_post(blogname: str, postid: int, post: dict) -> bool:
    """Caches a post. content parameter should contain HTML
    content of the post. If the post has already been cached
    and the contents haven't changed, returns True, else returns
    False."""

    ret = False
    if f"{blogname}-{postid}" not in cache["posts"]:
        ret = True
    elif cache["posts"][f"{blogname}-{postid}"]["post"] == post:
        ret = True

    cache["posts"][f"{blogname}-{postid}"] = {"cache_time": time.time(), "post": post}
    save_cache()

    return ret


def get_cached_post(blogname: str, postid: int) -> dict:
    """Returns a cached post, as received from Tumblr's API."""
    return cache["posts"][f"{blogname}-{postid}"]["post"]


def poll_needs_caching(blogname, postid, pollid) -> bool:
    if f"{blogname}-{postid}-{pollid}" not in cache["polls"]:
        print("poll needs caching!")
        return True

    poll = cache["polls"][f"{blogname}-{postid}-{pollid}"]
    created_at = dateutil.parser.parse(poll["created_at"])
    expire_delta = datetime.timedelta(seconds=poll["settings"]["expire_after"])
    end_time = created_at + expire_delta
    now = datetime.datetime.now(datetime.timezone.utc)
    is_over = end_time <= now

    return not is_over

def cache_poll(blogname: str, postid: int, poll: dict) -> bool:
    """Caches a poll. content parameter should contain HTML
    content of the poll. If the poll has already been cached
    and the contents haven't changed, returns True, else returns
    False."""
    pollid = poll["client_id"]
    ret = False
    if f"{blogname}-{postid}-{pollid}" not in cache["polls"]:
        ret = True
    elif cache["polls"][f"{blogname}-{postid}-{pollid}"] == poll:
        ret = True

    cache["polls"][f"{blogname}-{postid}-{pollid}"] = poll
    save_cache()

    return ret

def get_cached_poll(blogname: str, postid: int, pollid: str):
    return cache["polls"][f"{blogname}-{postid}-{pollid}"]
