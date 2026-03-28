# SPDX-License-Identifier: MIT
"""Data classes representing Tumblr data objects."""

import mimetypes
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Self

from markupsafe import Markup

if TYPE_CHECKING:
    # Placed in TYPE_CHECKING due to circular import
    from .api import TumblrAPI
    from .npf import NPFPost


##
# Media objects
# https://www.tumblr.com/docs/npf#media-objects
##


@dataclass
class Media:
    """Information about a single piece of media."""

    #: Mimetype of the media.
    type: str
    #: URL to the media.
    url: str
    #: Width of the media, if applicable.
    width: int | None
    #: Height of the media, if applicable.
    height: int | None
    #: Whether or not the media has its original dimensions.
    has_original_dimensions: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a media dict into a Media object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        if "type" not in data:
            _type = mimetypes.guess_type(data["url"].replace(".pnj", ".jpg"))[0]
            if _type is None:
                _type = ""
        else:
            _type = data["type"]

        return cls(
            type=_type,
            url=data["url"],
            width=data.get("width", None),
            height=data.get("height", None),
            has_original_dimensions=data.get("has_original_dimensions", False),
        )


class MediaList(list):
    """List of Media objects. Provides a convenience method for finding media of a specific size."""

    @property
    def no_dimensions(self) -> bool:
        """
        Check if the media in this list has no width/height.

        :returns: True if the media contained in the list is dimensionless,
        i.e. is not an image or video.
        """
        for media in self:
            if media.width is None or media.height is None:
                return True
        return False

    @property
    def original_dimensions(self) -> tuple[int, int] | None:
        """
        Get the original dimensions of the media, if present.

        :returns: Tuple of width and height, or None if original dimensions could
            not be determined.
        """
        if self.no_dimensions:
            return None

        for media in self:
            if media.has_original_dimensions:
                return (media.width, media.height)
        return None

    def get_hq(self) -> Media | None:
        """
        Find the highest-quality Media object.

        Returns either the media with original dimensions or the largest available
        media.

        :returns: Media object representing highest-quality media, or None if the list
            is empty.
        """
        if self.no_dimensions:
            return None

        if not self:
            return None

        _self_sorted = sorted(self, key=lambda m: m.width, reverse=True)

        for media in _self_sorted:
            if media.has_original_dimensions:
                return media

        return _self_sorted[0]

    def get_by_width(self, target_width: int) -> Media | None:
        """
        Find the closest Media object that fits the given width.

        :param target_width: Width to target.
        :returns: A matching Media object, or None if the list is empty.
        """
        if self.no_dimensions:
            return None

        if not self:
            return None

        _self_sorted = sorted(self, key=lambda m: m.width, reverse=True)

        for media in _self_sorted:
            if media.width <= target_width:
                return media

        return _self_sorted[-1]

    @classmethod
    def from_list_of_dicts(cls, data: list) -> Self:
        """Convert a list of media dicts to a MediaList."""
        out = cls()

        for m_data in data:
            out.append(Media.from_dict(m_data))

        return out


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
    avatars: MediaList

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
            avatars=MediaList.from_list_of_dicts(data.get("avatar", [])),
            is_broken=False,
        )

    @classmethod
    def create_dummy(cls, username: str) -> Self:
        """Create a dummy Blog object for a deleted blog."""
        return cls(
            uuid="",
            name=username,
            url=None,
            avatars=MediaList(),
            is_broken=True,
        )


@dataclass
class PostReblogInfo:
    """Represents the reblog info of a post."""

    #: Blog that the post was reblogged from.
    blog: Blog

    # TODO: Check if the theory about the latter two being missing for deleted
    # posts is correct

    #: ID of the post this post was reblogged from, or None if the post was
    #: deleted.
    post_id: int | None
    #: URL from which the post was reblogged, or None if the post was deleted.
    post_url: str | None

    @classmethod
    def from_api(
        cls, data: dict, prefix: Literal["reblogged_from"] | Literal["reblogged_root"]
    ) -> Self | None:
        """
        Create a PostReblogInfo object from post data.

        :param data: Post data.
        :param prefix: Prefix for data fetching; either reblogged_from
            or reblogged_root.
        :returns: Resulting PostReblogInfo object, or None if there is no
            reblog data.
        """

        # Use reblogged_(from,root) to get the data
        if prefix + "_name" in data:
            try:
                blog = Blog(
                    name=data[prefix + "_name"],
                    uuid=data[prefix + "_uuid"],
                    url="https://www.tumblr.com/blog/" + data[prefix + "_name"],
                    avatars=MediaList(),
                )
            except KeyError:
                # No reblogged_from_uuid; broken blog? (TODO verify)
                blog = Blog.create_dummy(data[prefix + "_name"])

            return cls(
                blog=blog,
                post_id=data.get(prefix + "_id"),
                post_url=data.get(prefix + "_url"),
            )

        # If there is no reblog data, try to guess from parent_post_url
        elif prefix == "reblogged_from" and "parent_post_url" in data:
            # https://www.tumblr.com/blog/view/(username)/
            if data["parent_post_url"].startswith("https://www.tumblr.com/blog/view/"):
                split = data["parent_post_url"][33:].split("/")
                blog = Blog.create_dummy(split[0])
                return cls(
                    blog=blog, post_id=int(split[1]), post_url=data["parent_post_url"]
                )

            # https://(username).tumblr.com/post/(id)/(slug)
            elif "tumblr.com/post/" in data["parent_post_url"]:
                username, rest = data["parent_post_url"][8:].split(".", 1)
                post_id = int(rest.split("/")[2])
                return cls(
                    blog=Blog.create_dummy(username),
                    post_id=post_id,
                    post_url=data["parent_post_url"],
                )

        # If there is no parent post URL, try to guess from last trail item
        elif prefix == "reblogged_root" and data["trail"]:
            last_trail_item = data["trail"][-1]

            if "broken_blog_name" in last_trail_item:
                blog = Blog.create_dummy(last_trail_item["broken_blog_name"])
            else:
                blog = Blog.from_api(data["trail"][-1]["blog"])

            if "post" in data and "id" in data["post"]:
                return cls(
                    blog=blog,
                    post_id=int(data["post"]["id"]),
                    post_url=f"https://www.tumblr.com/blog/view/{blog.name}/{data['post']['id']}",
                )

            return cls(blog=blog, post_id=None, post_url=None)

        # If none of the above matched, give up
        return None


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
    #: List of tags on the post.
    tags: list[str]

    #: Whether this post is a reblog.
    is_reblog: bool

    #: Reblog data for the post this post was reblogged from;
    #: None if the post is not a reblog or the reblog data is missing.
    reblogged_from: PostReblogInfo | None

    #: Reblog data for the root post this post was reblogged from;
    #: None if the post is not a reblog or the reblog data is missing.
    reblogged_root: PostReblogInfo | None

    #: List of NPFPost objects representing each "post" that makes up this
    #: post - first the reblog trail, then the post itself.
    #:
    #: Note that this is different from Tumblr's definition of the trail,
    #: which specifically covers only the reblog trail; we include the post
    #: itself at the end for ease-of-use.
    trail: list["NPFPost"]

    @classmethod
    def from_api(cls, data: dict) -> Self:
        """
        Turn a data dict received from the API into a Post object.

        :param data: Data to create the Post object from.
        :returns: the resulting Post object.
        """

        # Lazy import to avoid circular dependency
        from .npf import NPFPost

        is_reblog = False
        if (
            "parent_post_url" in data
            or "reblogged_from_name" in data
            or "reblogged_root_name" in data
        ):
            is_reblog = True

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
            is_reblog=is_reblog,
            reblogged_from=PostReblogInfo.from_api(data, "reblogged_from"),
            reblogged_root=PostReblogInfo.from_api(data, "reblogged_root"),
            trail=trail,
            tags=data["tags"],
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
            out += "\n\n"
            i += 1

        return out.strip()


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
