# SPDX-License-Identifier: MIT
"""Tests for the post embedding functionality."""

from fxtumblr.embed.meta import MetaImageEmbed, MetaVideoEmbed
from fxtumblr.post_embed import PostEmbed
from fxtumblr.render import RenderFiletype
from fxtumblr.render.paths import get_render_url
from fxtumblr.tumblr import TumblrAPI


async def test_post_embed_render_heuristics(tumblr_api: TumblrAPI):
    """Test render heuristics for posts."""

    to_test: list[tuple[str, int, bool]] = [
        # Blog      Post ID             Has video?
        ("knuxify", 811047603701694464, False),  # Text block with inline formatting
        ("knuxify", 811047588066476032, False),  # Text block with subtype
        ("knuxify", 730903802869317632, True),  # Various non-text blocks
        ("knuxify", 811081495873814528, False),  # Answer to ask
    ]

    for blog_name, post_id, has_video in to_test:
        print(f"Testing {blog_name}-{post_id}")

        post = await tumblr_api.get_post(blog_name, post_id, skip_cache=True)
        assert post is not None
        post_embed = PostEmbed.from_post(post)

        assert isinstance(post_embed, PostEmbed)
        assert post_embed.is_rendered is True
        assert isinstance(post_embed.meta_embed, MetaImageEmbed)
        if has_video:
            assert (
                post_embed.meta_embed.description
                and "?video" in post_embed.meta_embed.description
            )
        else:
            assert not post_embed.meta_embed.description
        assert post_embed.meta_embed.url == get_render_url(
            blog_name, post_id, filetype=RenderFiletype.PNG
        )


async def test_post_embed_video(tumblr_api: TumblrAPI):
    """Test embeds with videos."""

    # Presence of video
    post = await tumblr_api.get_post("knuxify", 722920574030053376, skip_cache=True)
    assert post is not None
    post_embed = PostEmbed.from_post(post)

    assert isinstance(post_embed, PostEmbed)
    assert post_embed.is_rendered is False
    assert isinstance(post_embed.meta_embed, MetaVideoEmbed)
    assert post_embed.meta_embed.url is not None
