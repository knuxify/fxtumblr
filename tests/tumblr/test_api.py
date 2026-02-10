# SPDX-License-Identifier: MIT
"""Tests for Tumblr API access functions."""

import pytest

# from fxtumblr.tumblr.npf import NPFContent
from fxtumblr.tumblr.api import PrivateBlogException, TumblrAPIException
from fxtumblr.tumblr.types import Blog, PollResults, Post


async def test_get_blog(tumblr_api):
    """Test blog fetching."""

    # Test regular blog
    blog = await tumblr_api.get_blog("knuxify", skip_cache=True)

    assert blog is not None
    assert isinstance(blog, Blog)
    assert blog.name == "knuxify"

    # Test 404
    blog = await tumblr_api.get_blog("a", skip_cache=True)
    assert blog is None

    # Test private blog with and without raise_on_private_blog
    blog = await tumblr_api.get_blog(
        "private-blog-test", skip_cache=True, raise_on_private_blog=False
    )
    assert blog is None

    with pytest.raises(PrivateBlogException):
        await tumblr_api.get_blog(
            "private-blog-test", skip_cache=True, raise_on_private_blog=True
        )


async def test_get_post(tumblr_api):
    """Test post fetching."""

    for username, post_id in (
        ("punkitt-is-here", 781681205274886144),
        ("knuxify", 730903802869317632),
        ("knuxify", 799921945450840064),
    ):
        # Test regular post
        post = await tumblr_api.get_post(username, post_id, skip_cache=True)

        assert post is not None
        assert isinstance(post, Post)
        assert post.blog.name == username
        assert post.id == post_id

    # Test 404
    post = await tumblr_api.get_post("knuxify", 1234, skip_cache=True)
    assert post is None

    # Test post_id=0 (returns multiple posts)
    post = await tumblr_api.get_post("knuxify", 0, skip_cache=True)
    assert post is None

    # Test non-existent blog
    post = await tumblr_api.get_post("a", 1234, skip_cache=True)
    assert post is None

    # Test private blog with and without raise_on_private_blog
    post = await tumblr_api.get_post(
        "private-blog-test",
        808188296199094272,
        skip_cache=True,
        raise_on_private_blog=False,
    )
    assert post is None

    with pytest.raises(PrivateBlogException):
        await tumblr_api.get_post(
            "private-blog-test",
            808188296199094272,
            skip_cache=True,
            raise_on_private_blog=True,
        )


async def test_get_poll_results(tumblr_api):
    """Test poll result fetching."""

    # Test regular poll results
    poll = await tumblr_api.get_poll_results(
        "knuxify",
        730903802869317632,
        "e040d07a-ca6a-4751-8df5-ebaa1719222e",
        skip_cache=True,
    )
    assert poll is not None
    assert isinstance(poll, PollResults)

    # Test 404 (nonexistent poll)
    poll = await tumblr_api.get_poll_results(
        "knuxify",
        730903802869317632,
        "f040d07a-ca6a-4751-8df5-ebaa1719222e",
        skip_cache=True,
    )
    assert poll is None

    # Test 404 (nonexistent post)
    poll = await tumblr_api.get_poll_results(
        "knuxify", 1234, "e040d07a-ca6a-4751-8df5-ebaa1719222e", skip_cache=True
    )
    assert poll is None

    # Test 404 (nonexistent blog)
    poll = await tumblr_api.get_poll_results(
        "a", 1234, "e040d07a-ca6a-4751-8df5-ebaa1719222e", skip_cache=True
    )
    assert poll is None

    # Test invalid poll ID
    with pytest.raises(TumblrAPIException):
        poll = await tumblr_api.get_poll_results(
            "knuxify", 730903802869317632, "bogus", skip_cache=True
        )
