# SPDX-License-Identifier: MIT
"""Tumblr API access functions."""

from dataclasses import dataclass
from json.decoder import JSONDecodeError
from typing import Optional, Self

from authlib.integrations.httpx_client import AsyncOAuth1Client

from .. import logger
from ..cache import cache
from .types import Blog, PollResults, Post


@dataclass
class TumblrAPIError:
    """Represents an error returned by Tumblr's API."""

    #: Human-readable title of the error.
    title: str
    #: Error code.
    code: int
    #: Extra detail text.
    detail: str | None = None

    @classmethod
    def from_api(cls, data: dict) -> Self:
        """Create a TumblrAPIError from an error dict."""
        return cls(
            title=data.get("title", "Unknown error"),
            code=data.get("code", 500),
            detail=data.get("detail", None),
        )


@dataclass
class TumblrAPIResponse:
    """Tumblr API response."""

    #: Raw JSON data as a dictionary.
    raw: dict

    #: The status code of the response, according to the "meta" array.
    status: int

    #: List of errors returned by the API.
    errors: list[TumblrAPIError]

    #: Response, if applicable.
    response: dict | None = None

    @classmethod
    def from_api(cls, data: dict) -> Self:
        """Convert dict-ified JSON data from the Tumblr API to a TumblrAPIResponse object."""
        if "errors" in data:
            errors = [TumblrAPIError.from_api(err) for err in data["errors"]]
        else:
            errors = []

        return cls(
            status=data.get("meta", {}).get("status", 500),
            errors=errors,
            response=data.get("response", None) or None,
            raw=data,
        )


class TumblrAPIException(Exception):
    """Exception class for Tumblr API methods."""

    errors: list[TumblrAPIError]

    @classmethod
    def from_response(cls, response: TumblrAPIResponse) -> Self:
        """Create a new TumblrAPIException from a TumblrAPIResponse."""
        if len(response.errors) == 0:
            ret = cls(f"Error: Unknown error ({response.status})")

        elif len(response.errors) == 1:
            error = response.errors[0]
            if error.detail:
                ret = cls(f"Error: {error.title}; {error.detail} ({error.code})")
            else:
                ret = cls(f"Error: {error.title} ({error.code})")

        else:
            error_str = f"{len(response.errors)} errors:\n"
            for error in response.errors:
                if error.detail:
                    error_str += f" - {error.title}; {error.detail} ({error.code}))\n"

                else:
                    error_str += f" - {error.title} ({error.code}))\n"
            ret = cls(error_str)

        ret.errors = response.errors

        return ret


class PrivateBlogException(Exception):
    """
    Custom exception for private blogs, which can be enabled
    for get_blog and get_post endpoints for more granular error handling.
    """


class TumblrAPI:
    """Provides access to the Tumblr API and handles caching."""

    #: Tumblr API base URL. Can be changed for testing.
    api_base = "https://api.tumblr.com"

    def __init__(self, consumer_key: str, consumer_secret: str):
        """
        Initialize the TumblrAPI object.

        :param consumer_key: Tumblr API access consumer key.
        :param consumer_secret: Tumblr API access consumer secret.
        """

        #: Tumblr API access consumer key.
        self.consumer_key: str = consumer_key
        #: Tumblr API access consumer secret.
        self.consumer_secret: str = consumer_secret

        #: httpx client for connections.
        self.client = AsyncOAuth1Client(
            self.consumer_key,
            self.consumer_secret,
            headers={"User-Agent": "fxtumblr v2 (https://github.com/knuxify/fxtumblr)"},
        )

    async def _get(
        self, api_url: str, params: Optional[dict] = None
    ) -> TumblrAPIResponse:
        """
        Get data from the Tumblr API.

        Called internally from other functions in the class.

        :param api_url: API to get the data for, without the https://api.tumblr.com/v2
            prefix.
        """
        if params is None:
            _params = {"api_key": self.consumer_key}
        else:
            _params = params.copy()
            _params["api_key"] = self.consumer_key

        url = f"{self.api_base}{'/' if not api_url.startswith('/') else ''}{api_url}"

        logger.debug(f"Tumblr API query: {url}, params {_params}")

        # Typing ignore; authlib type stubs are incorrect and claim .get
        # does not exist (it does)
        r = await self.client.get(url, params=_params)  # type: ignore[attr-defined]

        try:
            data = r.json()
        except JSONDecodeError:
            logger.error(
                f"Invalid response from Tumblr: {r.status_code}, text:\n{r.text}"
            )
            return TumblrAPIResponse(
                status=500,
                errors=[
                    TumblrAPIError(
                        code=500,
                        title="Failed to parse API data as JSON; likely something is wrong with Tumblr",
                    ),
                ],
                raw={},
            )

        # import json
        # print(f"\nTumblr API query: {url}, params {_params}\n")
        # print(json.dumps(data))
        # from pprint import pprint
        # pprint(data)

        return TumblrAPIResponse.from_api(data)

    async def get_blog(
        self,
        blog_id: str,
        skip_cache: bool = False,
        raise_on_private_blog: bool = False,
    ) -> Blog | None:
        """
        Get information about a blog with the given identifier.

        :param blog_id: Blog identifier: username, URL or ID.
        :param skip_cache: If True, always skips the cache.
        :param raise_on_private_blog: If True, and the blog is private,
            raises PrivateBlogException.
        :returns: Blog object representing the blog if it was found, None otherwise.
        :raises TumblrAPIException: if the API returns an error.
        :raises PrivateBlogException: if the blog is private and
            raise_on_private_blog is set.
        """
        cache_key: str = f"fxt-blog:{blog_id}"

        if not skip_cache:
            cached_data = await cache.get_json(cache_key)
            if cached_data:
                return Blog.from_api(cached_data)

        resp = await self._get(f"/v2/blog/{blog_id}/info")

        if resp.status == 200 and resp.response:
            if "blog" in resp.response:
                blog_data = resp.response["blog"]
                blog = Blog.from_api(blog_data)
                # Set cache keys for both blog ID and blog name
                if not skip_cache:
                    await cache.set_json(f"fxt-blog:{blog.uuid}", blog_data)
                    await cache.set_json(f"fxt-blog:{blog.name}", blog_data)
                return blog
            else:
                return None

        elif resp.status == 404:
            # Handle private blog
            if raise_on_private_blog and resp.errors[0].code == 4012:
                raise PrivateBlogException
            return None

        else:
            raise TumblrAPIException.from_response(resp)

    async def get_post(
        self,
        blog_id: str,
        post_id: int,
        skip_cache: bool = False,
        fetch_poll_results: bool = True,
        raise_on_private_blog: bool = False,
    ) -> Post | None:
        """
        Get a post from the blog with the given identifier.

        Posts are always fetched in NPF format.

        :param blog_id: Blog identifier: username, URL or ID.
        :param post_id: Post ID.
        :param skip_cache: If True, always skips the cache.
        :param fetch_poll_results: If True (the default), fetches poll results
            for all polls in the post. This requires additional API calls; if
            such behavior is undesirable, set this to False.
        :param raise_on_private_blog: If True, and the blog is private,
            raises PrivateBlogException.
        :returns: Post object representing the post if it was found, None otherwise.
        :raises TumblrAPIException: if the API returns an error.
        :raises PrivateBlogException: if the blog is private and
            raise_on_private_blog is set.
        """
        cache_key: str = f"fxt-post:{blog_id}:{post_id}"

        if not skip_cache:
            cached_data = await cache.get_json(cache_key)
            if cached_data:
                post = Post.from_api(cached_data)

                if fetch_poll_results:
                    await post.fetch_poll_results(self, skip_cache=skip_cache)

                return post

        resp = await self._get(
            f"/v2/blog/{blog_id}/posts", params={"id": post_id, "npf": "true"}
        )

        if resp.status == 200 and resp.response:
            if "posts" in resp.response and resp.response["posts"]:
                # It is possible for the API to return multiple posts (e.g. if post_id=0);
                # double-check that we actually extract the correct post here.
                for post_data in resp.response["posts"]:
                    if post_data["id"] == post_id:
                        post = Post.from_api(post_data)

                        if fetch_poll_results:
                            await post.fetch_poll_results(self, skip_cache=skip_cache)

                        if not skip_cache:
                            await cache.set_json(cache_key, post_data)

                        return post
                return None
            else:
                return None

        elif resp.status == 404:
            # Handle private blog
            if raise_on_private_blog and resp.errors[0].code == 4012:
                raise PrivateBlogException
            return None

        else:
            raise TumblrAPIException.from_response(resp)

    async def get_poll_results(
        self, blog_id: str, post_id: int, poll_id: str, skip_cache: bool = False
    ) -> PollResults | None:
        """
        Get results for the poll with the given ID.

        :param blog_id: Blog identifier: username, URL or ID.
        :param post_id: Post ID.
        :param poll_id: ID of the poll.
        :param skip_cache: If True, always skips the cache.
        :returns: PollResults object representing the post if it was found, None otherwise.
        :raises TumblrAPIException: if the API returns an error.
        """
        cache_key: str = f"fxt-poll:{blog_id}:{post_id}:{poll_id}"

        if not skip_cache:
            cached_data = await cache.get_json(cache_key)
            if cached_data:
                return PollResults.from_api(cached_data)

        resp = await self._get(f"/v2/polls/{blog_id}/{post_id}/{poll_id}/results")

        if resp.status == 200 and resp.response:
            ret = PollResults.from_api(resp.response)
            if not skip_cache:
                await cache.set_json(cache_key, resp.response)
            return ret

        elif resp.status == 404:
            return None

        else:
            raise TumblrAPIException.from_response(resp)
