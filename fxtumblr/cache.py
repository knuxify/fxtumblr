"""
Contains code for managing the cache.
"""

import json
import os.path
import time

from .config import config

cache: dict = {}
if os.path.exists(config['cache_path']):
    with open(config['cache_path']) as cache_file:
        cache = json.load(cache_file)


def save_cache():
    with open(config['cache_path'], 'w+') as cache_file:
        json.dump(cache, cache_file)


def post_needs_caching(blogname, postid) -> bool:
    if f'{blogname}-{postid}' not in cache:
        return True
    if time.time() - cache[f'{blogname}-{postid}']['cache_time'] >= config['cache_expiry']:
        return True
    return False


def cache_post(blogname: str, postid: int, post: dict) -> bool:
    """Caches a post. content parameter should contain HTML
    content of the post. If the post has already been cached
    and the contents haven't changed, returns True, else returns
    False."""

    ret = False
    if f'{blogname}-{postid}' not in cache:
        ret = True
    elif cache[f'{blogname}-{postid}']['post'] == post:
        ret = True

    cache[f'{blogname}-{postid}'] = {
        'cache_time': time.time(),
        'post': post
    }
    save_cache()

    return ret


def get_cached_post(blogname: str, postid: int) -> dict:
    """Returns a cached post, as received from Tumblr's API."""
    return cache[f'{blogname}-{postid}']['post']
