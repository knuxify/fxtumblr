# SPDX-License-Identifier: MIT
"""Data classes representing Tumblr data objects."""

from dataclasses import dataclass
from typing import Self

from .npf import NPFPost


@dataclass
class Blog:
    """
    Represents a Tumblr blog.

    Note that this class only exposes some properties useful to fxtumblr;
    for a list of all properties, see Tumblr's API documentation.
    """

    # Username.
    name: str
    uuid: str
    url: str | None

    #: Whether or not this Blog object represents a deleted/suspended/otherwise
    #: "broken" blog.
    is_broken: bool = False

    @classmethod
    def from_api(cls, data: dict) -> Self:
        """
        Turn a data dict received from the API into a Blog object.

        :param data: Data to create the Blog object from.
        :returns: the resulting Blog object.
        """
        return cls(
            name=data["name"],
            uuid=data["uuid"],
            url=data["url"],
            is_broken=False,
        )

    @classmethod
    def create_dummy(cls, username: str) -> Self:
        """Create a dummy Blog object for a deleted blog."""
        return cls(
            uuid="",
            name=username,
            url=None,
            is_broken=True,
        )


@dataclass
class Post:
    """
    Represents a post on Tumblr.

    Note that this class only exposes some properties useful to fxtumblr;
    for a list of all properties, see Tumblr's API documentation.
    """

    #: ID of the post.
    id: int
    #: Blog which posted this post.
    blog: Blog
    #: URL to the post.
    post_url: str

    #: List of NPFPost objects representing each "post" that makes up this
    #: post - first the reblog trail, then the post itself.
    trail: list[NPFPost]

    @classmethod
    def from_api(cls, data: dict) -> Self:
        """
        Turn a data dict received from the API into a Post object.

        :param data: Data to create the Post object from.
        :returns: the resulting Post object.
        """

        trail = []
        if "trail" in data:
            for i in data["trail"]:
                trail.append(NPFPost.from_trail_dict(i))
        trail.append(NPFPost.from_post_dict(data))

        return cls(
            blog=Blog.from_api(data["blog"]),
            id=data["id"],
            post_url=data["post_url"],
            trail=trail,
        )


@dataclass
class Poll:
    """Represents a poll under a post."""

    @classmethod
    def from_api(cls, data: dict) -> Self:
        """
        Turn a data dict received from the API into a Poll object.

        :param data: Data to create the Poll object from.
        :returns: the resulting Poll object.
        """
        return cls()
