# SPDX-License-Identifier: MIT
"""Code for generating post embeds."""

import random
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
    LayoutBlockRows,
)
from .tumblr.types import Post


@dataclass
class PostEmbed:
    """Embed representing a post."""

    #: HTML meta embed representing the post.
    meta_embed: MetaEmbed

    #: Whether the embed contains a render; if True, it's rendered, if False,
    #: it's a regular embed.
    is_rendered: bool

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
            # If the post has fancy layouts, it should be rendered
            for layout in npf_post.layout:
                if isinstance(layout, LayoutBlockRows):
                    if layout.truncate_after:
                        should_render = True
                    else:
                        for display in layout.display:
                            if len(display.blocks) > 1:
                                should_render = True
                                break
                else:
                    should_render = True

            for block in npf_post.content:
                # Save text blocks; while most can be represented in Markdown,
                # some have formatting that wouldn't be preserved
                if isinstance(block, ContentBlockText):
                    if block.formatting:
                        should_render = True
                    if block.subtype:
                        should_render = True

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

                    videos.append(block)
                    if len(videos) > 1:
                        should_render = True

                # For all other blocks, suggest a render.
                else:
                    should_render = True

        if videos and images:
            should_render = True

        # Get post content in Markdown format.
        content = post.to_markdown()
        if post.tags:
            content += "\n\n(#" + " #".join(post.tags) + ")"

        # If the description ends up being too long, suggest a render.
        if (videos and len(content) > 256) or (not videos and len(content) > 349):
            should_render = True

        # Header: poster/reblog info
        if post.is_reblog and post.reblogged_from:
            if post.reblogged_from.blog.name == post.blog.name:
                header = post.blog.name + " 🔁"
            else:
                header = post.blog.name + " 🔁 " + post.reblogged_from.blog.name
        else:
            header = post.blog.name

        subheader = f"{post.note_count} notes"

        provider_name = config.instance.name
        if config.instance.motd:
            provider_name += " | " + random.choice(config.instance.motd)  # noqa: S311

        common_options = {
            # site_name and theme_color are set directly in the template
            "provider_name": provider_name,
            "provider_url": "https://" + config.instance.domain,
        }

        meta_embed: MetaEmbed

        if should_render:
            if videos:
                base_url = (
                    f"https://{config.instance.domain}/{post.blog.name}/{post.id}"
                )
                if len(videos) > 1:
                    common_options["description"] = (
                        f"Hint: You can get the raw video by pasting in the following link: {base_url}?video=(n), where (n) is the number of the video in the post (starting from 1)."
                    )
                elif len(videos) == 1:
                    common_options["description"] = (
                        f"Hint: You can get the raw video by pasting in the following link: {base_url}?video"
                    )

            meta_embed = MetaImageEmbed(
                **common_options,  # type: ignore[arg-type, ty:invalid-argument-type]
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

        return cls(meta_embed=meta_embed, is_rendered=should_render)
