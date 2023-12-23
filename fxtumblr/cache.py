"""
Contains code for managing the cache.
"""

import json
import time
import datetime
import dateutil
import redis

from .config import config

r = redis.Redis(
    host=config["redis_host"], port=config["redis_port"], password=config["redis_password"], decode_responses=True
)


def post_needs_caching(blogname, postid) -> bool:
    cached = r.hgetall(f"posts:{blogname}-{postid}")
    if not cached:
        return True
    if time.time() - float(cached["cache_time"]) >= config["cache_expiry"]:
        return True
    return False


def cache_post(blogname: str, postid: int, post: dict) -> None:
    """Caches a post."""
    if (
        r.hgetall(f"posts:{blogname}-{postid}")
        and get_cached_post(blogname, postid) == post
    ):
        return

    r.hset(
        f"posts:{blogname}-{postid}",
        mapping={"cache_time": time.time(), "post": json.dumps(post)},
    )


def get_cached_post(blogname: str, postid: int) -> dict:
    """Returns a cached post, as received from Tumblr's API."""
    return json.loads(r.hgetall(f"posts:{blogname}-{postid}")["post"])


def poll_needs_caching(blogname, postid, pollid) -> bool:
    poll = r.get(f"polls:{blogname}-{postid}-{pollid}")
    if not poll:
        return True

    poll = json.loads(poll)
    created_at = dateutil.parser.parse(poll["created_at"])
    expire_delta = datetime.timedelta(seconds=poll["settings"]["expire_after"])
    end_time = created_at + expire_delta
    now = datetime.datetime.now(datetime.timezone.utc)
    is_over = end_time <= now

    if is_over != poll["is_over"]:
        return True

    return not is_over


def cache_poll(blogname: str, postid: int, poll: dict) -> None:
    """Caches a poll."""
    poll = poll.copy()
    pollid = poll["client_id"]

    created_at = dateutil.parser.parse(poll["created_at"])
    expire_delta = datetime.timedelta(seconds=poll["settings"]["expire_after"])
    end_time = created_at + expire_delta
    now = datetime.datetime.now(datetime.timezone.utc)
    is_over = end_time <= now
    poll["is_over"] = is_over

    r.set(f"polls:{blogname}-{postid}-{pollid}", json.dumps(poll))


def get_cached_poll(blogname: str, postid: int, pollid: str) -> dict:
    return json.loads(r.get(f"polls:{blogname}-{postid}-{pollid}"))
