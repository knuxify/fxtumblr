# SPDX-License-Identifier: MIT
"""Code for generating embeds."""

import urllib.parse
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Self

from markupsafe import Markup

from . import config
from .tumblr.types import Blog, Post


class Modifier(StrEnum):
    """Embed modifiers."""


@dataclass
class Embed:
    """Standard embed data container."""

    type: ClassVar[str] = "standard"

    title: str | None = None
    description: str | None = None
    site_name: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    provider_name: str | None = None
    provider_url: str | None = None
    theme_color: str | None = None

    #: Binding of properties to meta tag names.
    _meta_binds: ClassVar[dict[str, list[str]]] = {
        "title": ["og:title", "twitter:title"],
        "description": ["og:description", "twitter:description"],
        "site_name": ["og:site_name"],
        "theme_color": ["theme-color"],
    }

    #: oEmbed properties.
    oembed_props: ClassVar[list[str]] = [
        "title",
        "description",
        "author_name",
        "author_url",
        "provider_name",
        "provider_url",
    ]

    @classmethod
    def from_blog(cls, blog: Blog) -> "ProfileEmbed":
        """
        Create an Embed object from a Tumblr blog.

        :param blog: The blog to use for embed generation.
        :returns: Embed object representing the embed for the blog.
        """
        return ProfileEmbed(title=blog.name)

    @classmethod
    def from_post(cls, post: Post, modifiers: list[Modifier] | None = None) -> Self:
        """
        Create an Embed object from a Tumblr post.

        :param post: The post to use for embed generation.
        :param modifiers: List of modifiers.
        :returns: Embed object representing the embed for the post.
        """

        if post.is_reblog and post.reblogged_from:
            if post.reblogged_from.name == post.blog.name:
                header = post.blog.name + " 🔁"
            else:
                header = post.blog.name + " 🔁 " + post.reblogged_from.name
        else:
            header = post.blog.name

        return cls(author_name=post.blog.name, title=header)

    def to_meta_tags(self, oembed_link: bool = False) -> Markup:
        """
        Convert the embed data to <meta> HTML tags.

        :param oembed_link: If True, also fills in the oEmbed link tag.
        :returns: Markup string containing <meta> tags; valid, safe HTML.
        """
        out = Markup("")

        if self.type == "video":
            out += Markup('<meta property="og:type" content="video.other"/>')
            out += Markup('<meta property="twitter:card" content="player"/>')
        elif self.type == "profile":
            out += Markup('<meta property="og:type" content="profile"/>')
            out += Markup('<meta property="twitter:card" content="summary"/>')
        else:
            out += Markup(
                '<meta property="twitter:card" content="summary_large_image""/>'
            )

        for prop, tags in self._meta_binds.items():
            value = getattr(self, prop)
            if value:
                for tag in tags:
                    out += Markup('<meta property="{tag}" content="{value}"/>').format(
                        tag=tag, value=value
                    )

        if oembed_link:
            out += Markup(
                '<link rel="alternate" type="application/json+oembed" href="{oembed_url}"/>'
            ).format(oembed_url=self.to_oembed_url())

        return out

    def to_oembed(self) -> dict[str, str | int]:
        """
        Convert the embed data to OEmbed format.

        :returns: Dict representing the OEmbed data.
        """

        out: dict[str, str | int] = {"version": "1.0"}

        if isinstance(self, ImageEmbed):
            out["type"] = "photo"
        elif isinstance(self, VideoEmbed):
            out["type"] = "video"
        else:
            out["type"] = "link"

        for prop in self.oembed_props:
            value = getattr(self, prop)
            if value:
                out[prop] = value

        return out

    def to_oembed_url(self) -> str:
        """Get the oEmbed data URL."""
        oembed = self.to_oembed()
        del oembed["version"]
        return (
            "https://"
            + config["instance"]["domain"]
            + "/_api/oembed.json?"
            + urllib.parse.urlencode(oembed)
        )


@dataclass
class ImageEmbed(Embed):
    """Photo/image embed containing an image."""

    type: ClassVar[str] = "image"

    url: str | None = None
    width: int = 0
    height: int = 0

    _meta_binds: ClassVar[dict[str, list[str]]] = Embed._meta_binds | {
        "url": ["og:image", "twitter:image"],
        "width": ["og:image:width"],
        "height": ["og:image:height"],
    }

    oembed_props: ClassVar[list[str]] = Embed.oembed_props + ["url", "width", "height"]


@dataclass
class VideoEmbed(Embed):
    """Video embed."""

    type: ClassVar[str] = "video"

    url: str | None = None
    width: int = 0
    height: int = 0
    thumbnail_url: str | None = None
    mimetype: str = "video/mp4"

    _meta_binds: ClassVar[dict[str, list[str]]] = Embed._meta_binds | {
        "url": ["og:url", "og:video", "og:video:secure_url", "twitter:player:stream"],
        "width": ["og:video:width", "twitter:player:width"],
        "height": ["og:video:height", "twitter:player:height"],
        "thumbnail_url": ["og:image", "twitter:image"],
        "mimetype": ["og:video:type", "twitter:player:stream:content_type"],
    }

    oembed_props: ClassVar[list[str]] = Embed.oembed_props + ["url", "width", "height"]


@dataclass
class ProfileEmbed(Embed):
    """Embed containing information about a profile."""

    type: ClassVar[str] = "profile"

    pfp_url: str | None = None

    _meta_binds: ClassVar[dict[str, list[str]]] = Embed._meta_binds | {
        "pfp_url": ["og:image", "twitter:image"],
    }


@dataclass
class Activity:
    """ActivityPub activity subset for rich Discord embeds."""
