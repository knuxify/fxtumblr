# SPDX-License-Identifier: MIT
"""Tumblr API access functions."""

from dataclasses import dataclass
from json.decoder import JSONDecodeError
from typing import Optional, Self

from authlib.integrations.httpx_client import AsyncOAuth1Client

from ..app import logger
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

    #: The status code of the response, according to the "meta" array.
    status: int

    #: Tuple of errors returned by the API.
    errors: tuple[TumblrAPIError] = tuple()

    #: Response, if applicable.
    response: dict | None = None

    @classmethod
    def from_api(cls, data: dict) -> Self:
        """Convert dict-ified JSON data from the Tumblr API to a TumblrAPIResponse object."""
        if "errors" in data:
            errors = tuple(TumblrAPIError.from_api(err) for err in data["errors"])
        else:
            errors = tuple()

        return cls(
            status=data.get("meta", {}).get("status", 500),
            errors=errors,
            response=data.get("response", None) or None,
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
                    error_str.append(
                        f" - {error.title}; {error.detail} ({error.code}))\n"
                    )

                else:
                    error_str.append(f" - {error.title} ({error.code}))\n")
            ret = error_str

        ret.errors = response.errors

        return ret


class TumblrAPI:
    """Provides access to the Tumblr API and handles caching."""

    #: Tumblr API base URL. Can be changed for testing.
    api_base = "https://api.tumblr.com/v2"

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

        r = await self.client.get(url, params=_params)

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
            )

        # import json
        # print(f"\nTumblr API query: {url}, params {_params}\n")
        # print(json.dumps(data))
        # from pprint import pprint
        # pprint(data)

        return TumblrAPIResponse.from_api(data)

    async def get_blog(self, blog_id: str, skip_cache: bool = False) -> Blog | None:
        """
        Get information about a blog with the given identifier.

        :param blog_id: Blog identifier: username, URL or ID.
        :param skip_cache: If True, always skips the cache.
        :returns: Blog object representing the blog if it was found, None otherwise.
        :raises TumblrAPIException: if the API returns an error.
        """
        resp = await self._get(f"/blog/{blog_id}/posts")

        if resp.status == 200:
            return Blog.from_api(resp.response)

        elif resp.status == 404:
            return None

        else:
            raise TumblrAPIException.from_response(resp)

    async def get_post(
        self,
        blog_id: str,
        post_id: int,
        skip_cache: bool = False,
        fetch_poll_results: bool = True,
    ) -> Post | None:
        """
        Get a post from the blog with the given identifier.

        Posts are always fetched in NPF format.

        :param blog_id: Blog identifier: username, URL or ID.
        :param post_id: Post ID.
        :param skip_cache: If True, always skips the cache.
        :param fetch_polls: If True (the default), fetches poll results for all polls
            in the post. This requires additional API calls; if such behavior
            is undesirable, set this to False.
        :returns: Post object representing the post if it was found, None otherwise.
        :raises TumblrAPIException: if the API returns an error.
        """
        resp = await self._get(
            f"/blog/{blog_id}/posts", params={"id": post_id, "npf": "true"}
        )

        if resp.status == 200:
            if "posts" in resp.response and resp.response["posts"]:
                # It is possible for the API to return multiple posts (e.g. if post_id=0);
                # double-check that we actually extract the correct post here.
                for post in resp.response["posts"]:
                    if post["id"] == post_id:
                        post = Post.from_api(resp.response["posts"][0])

                        # Fetch poll results
                        for tpost in post.trail:
                            for block in tpost.content:
                                if block.type == "poll":
                                    try:
                                        # mypy is unaware that the block type is correct,
                                        # since we don't want to pull in the whole import
                                        # just for this check, and only check the type
                                        # string.
                                        await block.fetch_results(  # type: ignore
                                            self, blog_id, post_id
                                        )
                                    except ValueError:
                                        continue

                        return post
                return None
            else:
                return None

        elif resp.status == 404:
            return None

        else:
            raise TumblrAPIException.from_response(resp)

    async def get_poll_results(
        self, blog_id: str, post_id: int, poll_id: int, skip_cache: bool = False
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
        resp = await self._get(f"/polls/{blog_id}/{post_id}/{poll_id}/results")

        if resp.status == 200:
            return PollResults.from_api(resp.response)

        elif resp.status == 404:
            return None

        else:
            raise TumblrAPIException.from_response(resp)
