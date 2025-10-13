# SPDX-License-Identifier: MIT
"""Tests for Tumblr API access functions."""

# from fxtumblr.tumblr.npf import NPFContent
from fxtumblr.tumblr.types import Post


async def test_get_post(tumblr_api):
    """Test post fetching."""

    for username, post_id in (
        ("punkitt-is-here", 781681205274886144),
        ("knuxify", 730903802869317632),
    ):
        # Test regular post
        post = await tumblr_api.get_post(username, post_id, skip_cache=True)

        assert post is not None
        assert isinstance(post, Post)
        assert post.blog.name == username
        assert post.id == post_id
        # assert isinstance(post.content, NPFContent)

    # Test 404
    post = await tumblr_api.get_post("knuxify", 1234, skip_cache=True)
    assert post is None

    # Test post_id=0 (returns multiple posts)
    post = await tumblr_api.get_post("knuxify", 0, skip_cache=True)
    assert post is None

    # Test non-existent blog
    post = await tumblr_api.get_post("a", 1234, skip_cache=True)
    assert post is None
