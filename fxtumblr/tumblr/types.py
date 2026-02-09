# SPDX-License-Identifier: MIT
"""Data classes representing Tumblr data objects."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from markupsafe import Markup

from .npf import NPFPost

if TYPE_CHECKING:
    # Placed in TYPE_CHECKING due to circular import
    from .api import TumblrAPI


@dataclass
class Avatar:
    """Represents a blog's avatar."""

    #: URL to the avatar image.
    url: str
    #: Width of the avatar.
    width: int
    #: Height of the avatar.
    height: int

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Create an Avatar object from avatar data.

        :param data: Data to create the Avatar object from.
        :returns: the resulting Avatar object.
        """
        return cls(url=data["url"], width=data["width"], height=data["height"])


@dataclass
class Blog:
    """
    Represents a Tumblr blog.

    Note that this class only exposes some properties useful to fxtumblr;
    for a list of all properties, see Tumblr's API documentation.
    """

    name: str
    uuid: str
    url: str | None

    #: Different sizes of avatars.
    avatars: list[Avatar]

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
            avatars=[Avatar.from_dict(data) for data in data.get("avatars", [])],
            is_broken=False,
        )

    @classmethod
    def create_dummy(cls, username: str) -> Self:
        """Create a dummy Blog object for a deleted blog."""
        return cls(
            uuid="",
            name=username,
            url=None,
            avatars=[],
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
    #: URL to the post, on the blog site.
    post_url: str
    #: URL to the post, in Tumblr's UI.
    dash_url: str
    #: Total amount of received notes.
    note_count: int

    #: List of NPFPost objects representing each "post" that makes up this
    #: post - first the reblog trail, then the post itself.
    #:
    #: Note that this is different from Tumblr's definition of the trail,
    #: which specifically covers only the reblog trail; we include the post
    #: itself at the end for ease-of-use.
    trail: list[NPFPost]

    @property
    def is_reblog(self) -> bool:
        """True if the post is a reblog, False otherwise."""

        # If the post has more than 1 item in self.trail (so, more than 0 items
        # in the reblog trail, besides itself), it's a reblog.

        return len(self.trail) > 1

    @property
    def reblogged_from(self) -> Blog | None:
        """
        Returns the blog from which this post was reblogged, or None if the
        post is not a reblog.
        """

        if len(self.trail) > 1:
            return self.trail[-2].blog
        return None

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

        blog = Blog.from_api(data["blog"])

        return cls(
            blog=blog,
            id=data["id"],
            post_url=data["post_url"],
            dash_url=f"https://tumblr.com/{blog.name}/{data['id']}",
            note_count=data["note_count"],
            trail=trail,
        )

    async def fetch_poll_results(self, api: "TumblrAPI", skip_cache: bool = False):
        """
        Fetch poll results for all polls in this post.

        :param api: TumblrAPI object to use for fetching.
        :param skip_cache: If True, ignores the cache.
        """
        for post in self.trail:
            await post.fetch_poll_results(api, skip_cache=skip_cache)

    def to_html(self, truncate: bool = False) -> Markup:
        """
        Convert the post content into an HTML representation.

        :param truncate: Whether or not to add the "read more" block after the
            cutoff passed in the truncate_after variable of the rows layout.
            For posts without a truncate_after setting, this option does nothing.
        :returns: A string with a valid HTML representation of the post.
        """
        out = Markup("")
        i = 0
        n_posts = len(self.trail)
        for post in self.trail:
            # If the post is a reblog, the last post in the trail will be empty.
            # Skip it while converting.
            if not post.content and i == (n_posts - 1):
                continue
            out += f"▪ {post.blog.name}:\n"
            out += post.to_html(truncate=truncate).strip()
            i += 1

        return out

    def to_markdown(self, truncate: bool = False) -> str:
        """
        Convert the post to Markdown.

        :param truncate: Whether or not to add the "read more" block after the
            cutoff passed in the truncate_after variable of the rows layout.
            For posts without a truncate_after setting, this option does nothing.
        :returns: a string containing a Markdown representation of the post.
        """
        out = ""
        i = 0
        n_posts = len(self.trail)
        for post in self.trail:
            # If the post is a reblog, the last post in the trail will be empty.
            # Skip it while converting.
            if not post.content and i == (n_posts - 1):
                continue
            out += f"▪ {post.blog.name}:\n"
            out += post.to_markdown(truncate=truncate).strip()
            i += 1

        return out


@dataclass
class PollResults:
    """Represents the results of a poll."""

    #: Results of the poll, as a dict where the keys are the IDs of the options,
    #: and the value is the amount of votes.
    results: dict[str, int]

    #: Timestamp of the poll results. Can be used to check against the poll
    #: closing timestamp.
    timestamp: int

    @classmethod
    def from_api(cls, data: dict) -> Self:
        """
        Turn a data dict received from the API into a PollResults object.

        :param data: Data to create the PollResults object from.
        :returns: the resulting PollResults object.
        """
        return cls(results=data["results"], timestamp=data["timestamp"])
