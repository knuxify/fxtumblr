# SPDX-License-Identifier: MIT
"""Tests for Tumblr NPF parsing functions."""

import json

from fxtumblr.tumblr.npf import (
    ContentBlockAudio,
    ContentBlockImage,
    ContentBlockLink,
    ContentBlockPoll,
    ContentBlockText,
    ContentBlockVideo,
    NPFPost,
)
from fxtumblr.tumblr.types import Blog

from ..conftest import _get_tumblr_test_data


def test_npf_post():
    """Test the NPFPost class."""
    with open(_get_tumblr_test_data("post_npftest.json")) as test_data:
        post = NPFPost.from_dict(json.load(test_data)["response"]["posts"][0])

    assert post is not None
    assert isinstance(post, NPFPost)

    assert isinstance(post.blog, Blog)
    assert not post.blog.is_broken
    assert post.blog.name == "knuxify"

    assert post.content
    assert post.layout


def test_block_text():
    """Test text content block functions."""

    examples = (
        ({"type": "text", "text": "This is a test post!"}, "This is a test post!"),
        (
            {
                "type": "text",
                "text": "This is a test post!",
                "formatting": [{"start": 0, "end": 1, "type": "bold"}],
            },
            "<b>T</b>his is a test post!",
        ),
        (
            {
                "type": "text",
                "text": "Test",
                "formatting": [{"start": 0, "end": 4, "type": "bold"}],
            },
            "<b>Test</b>",
        ),
        (
            {
                "type": "text",
                "text": "This is a test post!",
                "formatting": [
                    {"start": 0, "end": 7, "type": "bold"},
                    {"start": 0, "end": 7, "type": "italic"},
                ],
            },
            "<b><i>This is</i></b> a test post!",
        ),
        (
            {
                "type": "text",
                "text": "This is a test post!",
                "formatting": [
                    {"start": 5, "end": 7, "type": "bold"},
                    {"start": 0, "end": 9, "type": "italic"},
                ],
            },
            "<i>This <b>is</b> a</i> test post!",
        ),
        # Complex tag closing examples
        (
            {
                "type": "text",
                "text": "This is a test post!",
                "formatting": [
                    {"start": 0, "end": 7, "type": "bold"},
                    {"start": 3, "end": 9, "type": "italic"},
                ],
            },
            "<b>Thi<i>s is</i></b><i> a</i> test post!",
        ),
        (
            {
                "type": "text",
                "text": "This is a test post!",
                "formatting": [
                    {"start": 0, "end": 14, "type": "strikethrough"},
                    {"start": 0, "end": 7, "type": "bold"},
                    {"start": 3, "end": 9, "type": "italic"},
                ],
            },
            "<strike><b>Thi<i>s is</i></b><i> a</i> test</strike> post!",
        ),
    )

    """
    # TODO: Format cleanup/preprocessing
        (
            {
                "type": "text",
                "text": "This is a test post!",
                "formatting": [
                    {"start": 0, "end": 4, "type": "bold"},
                    {"start": 3, "end": 7, "type": "bold"},
                ],
            },
            "<b>This is</b> a test post!",
        ),
        (
            {
                "type": "text",
                "text": "This is a test post!",
                "formatting": [
                    {"start": 0, "end": 9, "type": "bold"},
                    {"start": 3, "end": 7, "type": "italic"},
                    {"start": 5, "end": 7, "type": "bold"},
                ],
            },
            "<b>Thi<i>s is</i> a</b> test post!",
        ),
    """

    for data, expected_result in examples:
        block = ContentBlockText.from_dict(data)
        assert isinstance(block, ContentBlockText)
        if "formatting" in data:
            assert block.formatting is not None
        assert block.to_html() == expected_result


def test_block_image():
    """Test image content block functions."""

    examples = (
        (
            {
                "type": "image",
                "media": [
                    {
                        "media_key": "1cc6f410b3bc53161f8fbd64d2b28b5a:5b2682c6837efa16-ae",
                        "type": "image/png",
                        "width": 560,
                        "height": 200,
                        "url": "https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/5b2682c6837efa16-ae/s640x960/ce8b82f18f36f7b124d718d21442714022a290aa.png",
                        "has_original_dimensions": True,
                    },
                    {
                        "media_key": "1cc6f410b3bc53161f8fbd64d2b28b5a:5b2682c6837efa16-ae",
                        "type": "image/png",
                        "width": 540,
                        "height": 193,
                        "url": "https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/5b2682c6837efa16-ae/s540x810/6f137a9569188e44de3d2e1014866f05d04b3b2f.png",
                    },
                    {
                        "media_key": "1cc6f410b3bc53161f8fbd64d2b28b5a:5b2682c6837efa16-ae",
                        "type": "image/png",
                        "width": 500,
                        "height": 179,
                        "url": "https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/5b2682c6837efa16-ae/s500x750/acd1e305e0702d9aaaa23ec7d57e07cb5eaa8f70.png",
                    },
                    {
                        "media_key": "1cc6f410b3bc53161f8fbd64d2b28b5a:5b2682c6837efa16-ae",
                        "type": "image/png",
                        "width": 400,
                        "height": 143,
                        "url": "https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/5b2682c6837efa16-ae/s400x600/29270caae0f323527b103c18c29be4ca597ea62a.png",
                    },
                    {
                        "media_key": "1cc6f410b3bc53161f8fbd64d2b28b5a:5b2682c6837efa16-ae",
                        "type": "image/png",
                        "width": 250,
                        "height": 89,
                        "url": "https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/5b2682c6837efa16-ae/s250x400/bf985fb0635a98c4621ec907b5e1c20f66c4a131.png",
                    },
                    {
                        "media_key": "1cc6f410b3bc53161f8fbd64d2b28b5a:5b2682c6837efa16-ae",
                        "type": "image/png",
                        "width": 100,
                        "height": 36,
                        "url": "https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/5b2682c6837efa16-ae/s100x200/2fbf5f778619044141e623e6a88c53ab8d726f7b.png",
                    },
                    {
                        "media_key": "1cc6f410b3bc53161f8fbd64d2b28b5a:5b2682c6837efa16-ae",
                        "type": "image/png",
                        "width": 75,
                        "height": 75,
                        "url": "https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/5b2682c6837efa16-ae/s75x75_c1/faf924e25ce42ff879be3691edf23d4037bbcd6b.png",
                        "cropped": True,
                    },
                ],
                "colors": {
                    "c0": "000000",
                    "c1": "393939",
                    "c2": "1d1d1d",
                    "c3": "6c6c6c",
                    "c4": "ffffff",
                },
                "alt_text": 'A crudely-drawn banner saying "The Ultimate Test Post". The "T" in "test" is replaced with the T from the Tumblr logo.',
            },
            '<figure class="tmblr-full"><img src="https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/5b2682c6837efa16-ae/s640x960/ce8b82f18f36f7b124d718d21442714022a290aa.png"/><span class="tmblr-alt-text-helper">ALT</span></figure>',
        ),
    )

    for data, expected_result in examples:
        block = ContentBlockImage.from_dict(data)
        assert isinstance(block, ContentBlockImage)
        assert block.to_html() == expected_result


def test_block_link():
    """Test link content block functions."""

    examples = (
        (
            {
                "type": "link",
                "url": "https://tumblr.com",
                "display_url": "https://tumblr.com",
                "title": "Today on Tumblr",
                "description": "Explore today’s picks from the Tumblr team.",
                "site_name": "Tumblr",
            },
            '<div class="link-embed"><div class="link-embed-top"><span class="link-title">Today on Tumblr</span></div><div class="link-embed-bottom"><span class="link-description">Explore today’s picks from the Tumblr team.</span><span class="link-sitename">Tumblr</span></div></div>',
        ),
    )

    for data, expected_result in examples:
        block = ContentBlockLink.from_dict(data)
        assert isinstance(block, ContentBlockLink)
        assert block.to_html() == expected_result


def test_block_video():
    """Test video content block functions."""

    examples = (
        (
            {
                "type": "video",
                "provider": "tumblr",
                "url": "https://va.media.tumblr.com/tumblr_s2dhynoXj51yk47jo.mp4",
                "media": {
                    "url": "https://va.media.tumblr.com/tumblr_s2dhynoXj51yk47jo.mp4",
                    "type": "video/mp4",
                    "width": 750,
                    "height": 544,
                },
            },
            "FIXME",
        ),
    )

    for data, expected_result in examples:
        block = ContentBlockVideo.from_dict(data)
        assert isinstance(block, ContentBlockVideo)
        assert block.to_html() == expected_result


def test_block_audio():
    """Test audio content block functions."""

    examples = (
        (
            {
                "type": "audio",
                "provider": "tumblr",
                "url": "https://64.media.tumblr.com/58138b56a8729251b81de4f6d401d2a9/86e7573156aa2ff2-29/651608e8278b463944dc2f22bae0bcf3a7f0ef62.mp3",
                "title": "Example Track",
                "artist": "Example Artist",
                "album": "Example Album",
                "media": {
                    "media_key": "58138b56a8729251b81de4f6d401d2a9:5b2682c6837efa16-ea",
                    "type": "audio/mpeg",
                    "url": "https://64.media.tumblr.com/58138b56a8729251b81de4f6d401d2a9/5b2682c6837efa16-ea/afe1a484a9c04fc15702c8ce9bdb1807d6631a94.mp3",
                },
                "poster": [
                    {
                        "media_key": "41023f06513343104e9520f824c44c95:5b2682c6837efa16-2a",
                        "type": "image/jpeg",
                        "width": 170,
                        "height": 258,
                        "url": "https://64.media.tumblr.com/41023f06513343104e9520f824c44c95/5b2682c6837efa16-2a/s250x400/daf29fc6b4c169a4b8513dc09321c2340f6d5311.jpg",
                    }
                ],
            },
            "FIXME",
        ),
    )

    for data, expected_result in examples:
        block = ContentBlockAudio.from_dict(data)
        assert isinstance(block, ContentBlockAudio)
        assert block.to_html() == expected_result


def test_block_poll():
    """Test poll content block functions."""

    examples = (
        (
            {
                "type": "poll",
                "client_id": "e040d07a-ca6a-4751-8df5-ebaa1719222e",
                "question": "A poll!",
                "answers": [
                    {
                        "client_id": "0e094aec-5f4a-42c3-aa5f-4dc79cebabe7",
                        "answer_text": "I love NPF!",
                    },
                    {
                        "client_id": "3fd6cbc9-a929-4a71-a9ea-945fc2bceee3",
                        "answer_text": "Why must thou do this to me, Tumblr.",
                    },
                ],
                "settings": {
                    "multiple_choice": False,
                    "close_status": "closed-after",
                    "expire_after": 86400,
                    "source": "tumblr",
                },
                "created_at": "2023-10-11 17:09:44 GMT",
                "timestamp": 1697044184,
            },
            "FIXME",
        ),
    )

    for data, expected_result in examples:
        block = ContentBlockPoll.from_dict(data)
        assert isinstance(block, ContentBlockPoll)
        assert block.to_html() == expected_result
