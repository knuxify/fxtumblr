# SPDX-License-Identifier: MIT
"""Code for generating embeds."""

import html
import urllib.parse
from dataclasses import dataclass
from typing import ClassVar, Self

from . import config
from .tumblr.types import Post


@dataclass
class Embed:
    """Standard embed data container."""

    title: str | None = None
    description: str | None = None
    site_name: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    provider_name: str | None = None
    provider_url: str | None = None
    theme_color: str | None = None

    is_profile: bool = False

    image_url: str | None = None
    video_url: str | None = None
    media_width: int = 0
    media_height: int = 0

    #: Binding of properties to meta tag names.
    _meta_binds: ClassVar[dict[str, list[str]]] = {
        "title": ["og:title", "twitter:title"],
        "description": ["og:description", "twitter:description"],
        "site_name": ["og:site_name"],
        "theme_color": ["theme-color"],
    }

    @classmethod
    def from_post(cls, post: Post) -> Self:
        """
        Create an Embed object from a Tumblr post.

        :param post: The post to use for embed generation.
        :returns: Embed object representing the embed for the post.
        """
        return cls()  # TODO

    def to_meta_tags(self, oembed_link: bool = False) -> str:
        """
        Convert the embed data to <meta> HTML tags.

        :param oembed_link: If True, also fills in the oEmbed link tag.
        :returns: String containing <meta> tags; valid, safe HTML.
        """
        out = ""

        for prop, tags in self._meta_binds.items():
            value = getattr(self, prop)
            if value and isinstance(value, str):
                value = html.escape(value)
                for tag in tags:
                    out += f'<meta property="{tag}" content="{value}"/>'

        if oembed_link:
            out += f'<link rel="alternate" type="application/json+oembed" href="{self.to_oembed_url()}"/>'

        return out

    def to_oembed(self) -> dict[str, str | int]:
        """
        Convert the embed data to OEmbed format.

        :returns: Dict representing the OEmbed data.
        """

        out: dict[str, str | int] = {"version": "1.0"}

        if self.image_url:
            out["type"] = "photo"
            out["url"] = self.image_url
            out["width"] = self.media_width
            out["height"] = self.media_height

        elif self.video_url:
            out["type"] = "video"
            out["url"] = self.video_url
            out["width"] = self.media_width
            out["height"] = self.media_height

        else:
            out["type"] = "link"

        for prop in (
            "title",
            "author_name",
            "author_url",
            "provider_name",
            "provider_url",
        ):
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
class Activity:
    """ActivityPub activity subset for rich Discord embeds."""
