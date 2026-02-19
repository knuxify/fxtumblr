# SPDX-License-Identifier: MIT
"""Code for generating post embeds."""

from dataclasses import dataclass
from typing import Self

from . import config
from .embed.meta import MetaEmbed, MetaImageEmbed, MetaVideoEmbed
from .render import RenderModifier
from .render.paths import get_render_url
from .tumblr.npf import (
    ContentBlockImage,
    ContentBlockText,
    ContentBlockVideo,
)
from .tumblr.types import Post


@dataclass
class PostEmbed:
    """Embed representing a post."""

    #: HTML meta embed representing the post.
    meta_embed: MetaEmbed

    @classmethod
    def from_post(
        cls,
        post: Post,
        render_modifiers: list[RenderModifier] | None = None,
        force_render: bool = False,
    ) -> Self:
        """
        Create an Embed object from a Tumblr post.

        :param post: The post to use for embed generation.
        :param render_modifiers: List of modifiers for the render.
        :param force_render: If True, forces an embed with a rendered post,
            rather than relying on heuristics.
        :returns: Embed object representing the embed for the post.
        """

        #: Whether the post should be rendered.
        should_render: bool = force_render
        # The initial state is based on force_render.

        #: List of images in the post.
        images: list[ContentBlockImage] = []
        #: List of videos in the post.
        videos: list[ContentBlockVideo] = []

        # Determine the post type by iterating over all posts.
        for npf_post in post.trail:
            for block in npf_post.content:
                # Text blocks can be nicely represented in Markdown
                if isinstance(block, ContentBlockText):
                    pass

                # Image: up to 1 image (right now only one is supported,
                # if/when activity embeds get added we will be able to use 4).
                elif isinstance(block, ContentBlockImage):
                    if len(images) < 1:
                        images.append(block)
                    else:
                        should_render = True

                # Video: up to 1 video
                elif isinstance(block, ContentBlockVideo):
                    # Do not include embedded videos (which have no media object)
                    if not block.media:
                        continue

                    if len(videos) < 1:
                        videos.append(block)
                    else:
                        should_render = True

                # For all other blocks, suggest a render.
                else:
                    should_render = True

        if videos and images:
            should_render = True

        # Get post content in Markdown format. If it ends up being too long,
        # suggest a render.
        content = post.to_markdown()
        if (videos and len(content) > 256) or (not videos and len(content) > 349):
            should_render = True

        # Header: poster/reblog info
        if post.is_reblog and post.reblogged_from:
            if post.reblogged_from.name == post.blog.name:
                header = post.blog.name + " 🔁"
            else:
                header = post.blog.name + " 🔁 " + post.reblogged_from.name
        else:
            header = post.blog.name

        subheader = f"{post.note_count} notes"

        common_options = {
            # site_name and theme_color are set directly in the template
            "provider_name": config.instance.name,
            "provider_url": "https://" + config.instance.domain,
        }

        meta_embed: MetaEmbed

        if should_render:
            meta_embed = MetaImageEmbed(
                **common_options,  # type: ignore[arg-type]
                title=header,
                author_name=subheader,
                author_url=post.dash_url,
                url=get_render_url(post.blog.name, post.id, render_modifiers),
            )
        else:
            if videos:
                video = videos[0].media
                # We already ensure that the videos have a media object earlier
                # in the function; mypy does not realize this, so we explicitly
                # specify it here
                assert video is not None

                if videos[0].poster:
                    thumbnail = videos[0].poster.get_by_width(320)
                    if not thumbnail:
                        thumbnail = videos[0].poster.get_hq()
                else:
                    thumbnail = None

                meta_embed = MetaVideoEmbed(
                    **common_options,
                    title=subheader + " | " + header,
                    description=content,
                    author_name=header,
                    author_url=post.dash_url,
                    url=video.url,
                    width=video.width or 0,
                    height=video.height or 0,
                    thumbnail_url=thumbnail.url if thumbnail else "",
                )
            elif images:
                image = images[0].media.get_hq()
                meta_embed = MetaImageEmbed(
                    **common_options,
                    title=header,
                    description=content,
                    author_name=subheader,
                    author_url=post.dash_url,
                    url=image.url if image else "",
                    width=(image.width or 0) if image else 0,
                    height=(image.height or 0) if image else 0,
                )
            else:
                meta_embed = MetaEmbed(
                    **common_options,
                    title=header,
                    description=content,
                    author_name=subheader,
                    author_url=post.dash_url,
                )

        return cls(meta_embed=meta_embed)
