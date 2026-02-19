# SPDX-License-Identifier: MIT
"""HTML meta tag embed provider."""

import urllib.parse
from dataclasses import dataclass
from typing import ClassVar

from markupsafe import Markup

from .. import config


@dataclass
class MetaEmbed:
    """Base class for embed providers."""

    type: ClassVar[str] = "standard"

    title: str | None = None
    description: str | None = None
    site_name: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    provider_name: str | None = None
    provider_url: str | None = None
    theme_color: str | None = None

    pfp_url: str | None = None

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
                '<meta property="twitter:card" content="summary_large_image"/>'
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

        if isinstance(self, MetaImageEmbed):
            out["type"] = "photo"
        elif isinstance(self, MetaVideoEmbed):
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
            + config.instance.domain
            + "/_api/oembed.json?"
            + urllib.parse.urlencode(oembed)
        )


@dataclass
class MetaImageEmbed(MetaEmbed):
    """Photo/image embed containing an image."""

    type: ClassVar[str] = "image"

    url: str | None = None
    width: int = 0
    height: int = 0

    _meta_binds: ClassVar[dict[str, list[str]]] = MetaEmbed._meta_binds | {
        "url": ["og:image", "twitter:image"],
        "width": ["og:image:width"],
        "height": ["og:image:height"],
    }

    oembed_props: ClassVar[list[str]] = MetaEmbed.oembed_props + [
        "url",
        "width",
        "height",
    ]


@dataclass
class MetaVideoEmbed(MetaEmbed):
    """Video embed."""

    type: ClassVar[str] = "video"

    url: str | None = None
    width: int = 0
    height: int = 0
    thumbnail_url: str | None = None
    mimetype: str = "video/mp4"

    _meta_binds: ClassVar[dict[str, list[str]]] = MetaEmbed._meta_binds | {
        "url": ["og:url", "og:video", "og:video:secure_url", "twitter:player:stream"],
        "width": ["og:video:width", "twitter:player:width"],
        "height": ["og:video:height", "twitter:player:height"],
        "thumbnail_url": ["og:image", "twitter:image"],
        "mimetype": ["og:video:type", "twitter:player:stream:content_type"],
    }

    oembed_props: ClassVar[list[str]] = MetaEmbed.oembed_props + [
        "url",
        "width",
        "height",
    ]


@dataclass
class MetaProfileEmbed(MetaEmbed):
    """Embed containing information about a profile."""

    type: ClassVar[str] = "profile"

    _meta_binds: ClassVar[dict[str, list[str]]] = MetaEmbed._meta_binds | {
        "pfp_url": ["og:image", "twitter:image"],
    }
