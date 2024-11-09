"""
Contains code for getting posts.
"""

import pytumblr
from pytumblr.request import TumblrRequest

# needed by FxTumblrRequest
import requests
import urllib.parse
from requests_oauthlib import OAuth1
from requests.exceptions import TooManyRedirects, HTTPError
import sys

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

from typing import List

# needed by FxTumblrRequest
PY3 = True


class FxTumblrRequest:
    """
    Custom fork of pytumblr.request.TumblrRequest that automatically rotates
    between multiple API keys.

    The original code can be found here: https://github.com/tumblr/pytumblr/blob/master/pytumblr/request.py
    and is licensed under the Apache 2.0 license.

    Please keep this up-to-date with upstream.
    """

    # __version = pytumblr.request.TumblrRequest.__version
    __version = "0.1.2"

    def __init__(self, credentials: List[List[str]]):
        """
        Initialize the FxTumblrRequest object.
        :param credentials: List of credentials as tuples of (key, secret).
        """

        self.host = "https://api.tumblr.com"

        self.requests = [
            TumblrRequest(consumer_key=cred[0], consumer_secret=cred[1], host=self.host)
            for cred in credentials
        ]
        #: Credentials to use. Incremented whenever one of the API keys gets ratelimited.
        self.current_cred = 0
        self._key_switches_since_fail = 0

    @property
    def headers(self):
        return self.requests[self.current_cred].headers

    @property
    def oauth(self):
        return self.requests[self.current_cred].oauth

    @property
    def consumer_key(self):
        return self.requests[self.current_cred].consumer_key

    def next_key(self) -> bool:
        """
        Switches over to the next key.

        Returns True if such a key was available, False if we run out of keys.
        """
        if self._key_switches_since_fail > len(self.requests):
            self._key_switches_since_fail = 0
            return False

        if (self.current_cred + 1) == len(self.requests):
            self_current_cred = 0
        else:
            self.current_cred += 1

        self._key_switches_since_fail += 1

        return True

    ### TumblrRequest code start ###

    def get(self, url, params):
        """
        Issues a GET request against the API, properly formatting the params

        :param url: a string, the url you are requesting
        :param params: a dict, the key-value of all the paramaters needed
                       in the request
        :returns: a dict parsed of the JSON response
        """
        url = self.host + url
        if params:
            url = url + "?" + urllib.parse.urlencode(params)

        try:
            resp = requests.get(
                url, allow_redirects=False, headers=self.headers, auth=self.oauth
            )
        except TooManyRedirects as e:
            resp = e.response

        # WORKAROUND: Tumblr API bug: getting a banned(?) post ("This content has been
        # hidden due to its potentially sensitive nature" message) from a blog hidden
        # due to mature content returns a regular Tumblr 404 page instead of a
        # valid 404 JSON response.
        # We manually fix it up to return a 404, but this should probably be reported
        # to Tumblr and fixed on their end.
        if resp.status_code == 404 and "<!DOCTYPE html>" in resp.text:
            return {
                "meta": {"status": 404, "msg": "Not Found"},
                "errors": [
                    {
                        "title": "Not Found",
                        "code": 0,
                        "detail": "Tumblr bug: post has been evaporated and API returns 404 page.",
                    }
                ],
                "response": [],
            }

        # FxTumblrRequest modification start
        if resp.status_code == 429:
            if self.next_key():
                return self.get(url, params)
        else:
            self._key_switches_since_fail = 0
        # FxTumblrRequest modification end

        return self.json_parse(resp)

    def post(self, url, params={}, files=[]):
        """
        Issues a POST request against the API, allows for multipart data uploads

        :param url: a string, the url you are requesting
        :param params: a dict, the key-value of all the parameters needed
                       in the request
        :param files: a list, the list of tuples of files

        :returns: a dict parsed of the JSON response
        """
        url = self.host + url
        try:
            if files:
                return self.post_multipart(url, params, files)
            else:
                data = urllib.parse.urlencode(params)
                if not PY3:
                    data = str(data)
                resp = requests.post(
                    url, data=data, headers=self.headers, auth=self.oauth
                )

                # FxTumblrRequest modification start
                if resp.status_code == 429:
                    if self.next_key():
                        return self.post(url, params, files)
                else:
                    self._key_switches_since_fail = 0
                # FxTumblrRequest modification end

                return self.json_parse(resp)
        except HTTPError as e:
            # FxTumblrRequest modification start
            if e.response.status_code == 429:
                if self.next_key():
                    return self.post(url, params, files)
            else:
                self._key_switches_since_fail = 0
            # FxTumblrRequest modification end
            return self.json_parse(e.response)

    def delete(self, url, params):
        """
        Issues a DELETE request against the API, properly formatting the params

        :param url: a string, the url you are requesting
        :param params: a dict, the key-value of all the paramaters needed
                       in the request
        :returns: a dict parsed of the JSON response
        """
        url = self.host + url
        if params:
            url = url + "?" + urllib.parse.urlencode(params)

        try:
            resp = requests.delete(
                url, allow_redirects=False, headers=self.headers, auth=self.oauth
            )
        except TooManyRedirects as e:
            resp = e.response

        # FxTumblrRequest modification start
        if resp.status_code == 429:
            if self.next_key():
                return self.delete(url, params)
        else:
            self._key_switches_since_fail = 0
        # FxTumblrRequest modification end

        return self.json_parse(resp)

    ### TumblrRequest code end ###

    def json_parse(self, response):
        if response is None:
            print(
                "Error when parsing Tumblr JSON response: no response", file=sys.stderr
            )
        else:
            try:
                response.json()
            except ValueError:
                try:
                    print(
                        f"Error when parsing Tumblr JSON response: status code {response.status_code}, content:\n{response.text}",
                        file=sys.stderr,
                    )
                except:
                    print(
                        f"Error when parsing Tumblr JSON response: malformed response object {response}",
                        file=sys.stderr,
                    )

        return TumblrRequest.json_parse(self, response)

    def post_multipart(self, url, params, files):
        return TumblrRequest.post_multipart(self, url, params, files)


if config.get("tumblr_api_keys", []):
    tumblr = pytumblr.TumblrRestClient(
        "",
        "",
        None,
        None,
    )
    tumblr.request = FxTumblrRequest(credentials=config["tumblr_api_keys"])
else:
    tumblr = pytumblr.TumblrRestClient(
        config["tumblr_consumer_key"],
        config["tumblr_consumer_secret"],
        None,
        None,
    )

DEFAULT_AVATAR = "https://assets.tumblr.com/pop/src/assets/images/avatar/anonymous_avatar_40-3af33dc0.png"


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
            assert "errors" not in poll
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
        if not avatar_url:
            avatar_url = DEFAULT_AVATAR
        cache_avatar(blog_name, avatar_url)
    else:
        avatar_url = get_cached_avatar(blog_name)

    return avatar_url
