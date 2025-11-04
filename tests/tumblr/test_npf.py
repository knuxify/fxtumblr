# SPDX-License-Identifier: MIT
"""Tests for Tumblr NPF parsing functions."""

import json

import aiofiles

from fxtumblr.tumblr.npf import (
    ContentBlock,
    ContentBlockAudio,
    ContentBlockImage,
    ContentBlockLink,
    ContentBlockPoll,
    ContentBlockText,
    ContentBlockVideo,
    LayoutBlock,
    NPFPost,
    npf_to_html,
)
from fxtumblr.tumblr.types import Blog

from ..conftest import _get_tumblr_test_data


async def test_npf_post(tumblr_api):
    """Test the NPFPost class."""
    async with aiofiles.open(_get_tumblr_test_data("post_npftest.json")) as test_data:
        post = NPFPost.from_post_dict(
            json.loads(await test_data.read())["response"]["posts"][0]
        )

    assert post is not None
    assert isinstance(post, NPFPost)

    assert isinstance(post.blog, Blog)
    assert not post.blog.is_broken
    assert post.blog.name == "knuxify"

    assert post.content
    for content_block in post.content:
        assert isinstance(content_block, ContentBlock)

    assert post.layout
    for layout_block in post.layout:
        assert isinstance(layout_block, LayoutBlock)

    # The NPF test post has a poll, we need to fetch results before rendering to HTML
    await post.fetch_poll_results(tumblr_api, skip_cache=True)

    # Test post with ask
    async with aiofiles.open(_get_tumblr_test_data("post_ask.json")) as test_data:
        post = NPFPost.from_post_dict(
            json.loads(await test_data.read())["response"]["posts"][0]
        )

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
        (
            {"type": "text", "text": "This is a test post!"},
            "<p>This is a test post!</p>",
        ),
        (
            {
                "type": "text",
                "text": "This is a test post!",
                "formatting": [{"start": 0, "end": 1, "type": "bold"}],
            },
            "<p><b>T</b>his is a test post!</p>",
        ),
        (
            {
                "type": "text",
                "text": "Test",
                "formatting": [{"start": 0, "end": 4, "type": "bold"}],
            },
            "<p><b>Test</b></p>",
        ),
        (
            {
                "type": "text",
                "text": "AABBCCDD",
                "formatting": [
                    {"start": 1, "end": 2, "type": "bold"},
                    {"start": 5, "end": 6, "type": "bold"},
                ],
            },
            "<p>A<b>A</b>BBC<b>C</b>DD</p>",
        ),
        (
            {
                "type": "text",
                "text": "AABBCCDD",
                "formatting": [
                    {"start": 1, "end": 2, "type": "bold"},
                    {"start": 5, "end": 6, "type": "bold"},
                ],
            },
            "<p>A<b>A</b>BBC<b>C</b>DD</p>",
        ),
        (
            {
                "type": "text",
                "text": "AAAABBBB",
                "formatting": [
                    {"start": 4, "end": 8, "type": "bold"},
                    {"start": 0, "end": 8, "type": "italic"},
                ],
            },
            "<p><i>AAAA<b>BBBB</b></i></p>",
        ),
        (
            {
                "type": "text",
                "text": "AAAABBBB",
                "formatting": [
                    {"start": 4, "end": 8, "type": "italic"},
                    {"start": 0, "end": 8, "type": "bold"},
                ],
            },
            "<p><b>AAAA<i>BBBB</i></b></p>",
        ),
        (
            {
                "type": "text",
                "text": "AAAABBBB",
                "formatting": [
                    {"start": 0, "end": 4, "type": "bold"},
                    {"start": 0, "end": 8, "type": "italic"},
                ],
            },
            "<p><i><b>AAAA</b>BBBB</i></p>",
        ),
        (
            {
                "type": "text",
                "text": "AAAABBBB",
                "formatting": [
                    {"start": 0, "end": 4, "type": "italic"},
                    {"start": 0, "end": 8, "type": "bold"},
                ],
            },
            "<p><b><i>AAAA</i>BBBB</b></p>",
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
            "<p><b><i>This is</i></b> a test post!</p>",
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
            "<p><i>This <b>is</b> a</i> test post!</p>",
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
            "<p><b>Thi<i>s is</i></b><i> a</i> test post!</p>",
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
            "<p><strike><b>Thi<i>s is</i></b><i> a</i> test</strike> post!</p>",
        ),
        # Multi-codepoint emoji
        (
            {
                "type": "text",
                "text": "This is a 5-codepoint emoji 👨‍👨‍👦 post!",
                "formatting": [
                    {"start": 0, "end": 4, "type": "bold"},
                    {"start": 22, "end": 38, "type": "bold"},
                    {"start": 34, "end": 38, "type": "italic"},
                ],
            },
            "<p><b>This</b> is a 5-codepoint <b>emoji 👨‍👨‍👦 <i>post</i></b>!</p>",
        ),
        (
            {
                "type": "text",
                "text": "AA👨‍👨‍👦BB",
                "formatting": [
                    {"start": 2, "end": 7, "type": "bold"},
                ],
            },
            "<p>AA<b>👨‍👨‍👦</b>BB</p>",
        ),
        # Subtypes
        (
            {
                "type": "text",
                "text": "ab👨‍👨‍👦cd",
                "subtype": "heading1",
                "formatting": [
                    {"start": 2, "end": 7, "type": "bold"},
                ],
            },
            "<h1>ab<b>👨‍👨‍👦</b>cd</h1>",
        ),
        (
            {
                "type": "text",
                "text": "ab👨‍👨‍👦cd",
                "subtype": "heading2",
                "formatting": [
                    {"start": 2, "end": 7, "type": "bold"},
                ],
            },
            "<h2>ab<b>👨‍👨‍👦</b>cd</h2>",
        ),
        (
            {
                "type": "text",
                "text": "ab👨‍👨‍👦cd",
                "subtype": "ordered-list-item",
                "formatting": [
                    {"start": 2, "end": 7, "type": "bold"},
                ],
            },
            "<li>ab<b>👨‍👨‍👦</b>cd</li>",
        ),
        (
            {
                "type": "text",
                "text": "ab👨‍👨‍👦cd",
                "subtype": "unordered-list-item",
                "formatting": [
                    {"start": 2, "end": 7, "type": "bold"},
                ],
            },
            "<li>ab<b>👨‍👨‍👦</b>cd</li>",
        ),
        (
            {
                "type": "text",
                "text": "ab👨‍👨‍👦cd",
                "subtype": "chat",
                "formatting": [
                    {"start": 2, "end": 7, "type": "bold"},
                ],
            },
            '<p class="npf_chat">ab<b>👨‍👨‍👦</b>cd</p>',
        ),
        (
            {
                "type": "text",
                "text": "ab👨‍👨‍👦cd",
                "subtype": "quote",
                "formatting": [
                    {"start": 2, "end": 7, "type": "bold"},
                ],
            },
            '<p class="npf_quote">ab<b>👨‍👨‍👦</b>cd</p>',
        ),
        (
            {
                "type": "text",
                "text": "ab👨‍👨‍👦cd",
                "subtype": "quirky",
                "formatting": [
                    {"start": 2, "end": 7, "type": "bold"},
                ],
            },
            '<p class="npf_quirky">ab<b>👨‍👨‍👦</b>cd</p>',
        ),
        # Emoji styling
        (
            {
                "type": "text",
                "text": "😀😄😅",
            },
            '<p class="emoji-large">😀😄😅</p>',
        ),
        (
            {
                "type": "text",
                "text": "👨‍👨‍👦👨‍👨‍👦👨‍👨‍👦",
            },
            '<p class="emoji-large">👨‍👨‍👦👨‍👨‍👦👨‍👨‍👦</p>',
        ),
        (
            {
                "type": "text",
                "text": "test😀😄😅",
            },
            "<p>test😀😄😅</p>",
        ),
        (
            {
                "type": "text",
                "text": "😀😄😅test",
            },
            "<p>😀😄😅test</p>",
        ),
        (
            {
                "type": "text",
                "text": "😀<😄>😅",
            },
            "<p>😀&lt;😄&gt;😅</p>",
        ),
        (
            {
                "type": "text",
                "text": "😀<😄",
            },
            "<p>😀&lt;😄</p>",
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
            "<p><b>This is</b> a test post!</p>",
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
            "<p><b>Thi<i>s is</i> a</b> test post!</p>",
        ),
    """

    for data, expected_result in examples:
        block = ContentBlockText.from_dict(data)
        assert isinstance(block, ContentBlockText)
        if "formatting" in data:
            assert block.formatting is not None
        assert block.to_html() == expected_result


def test_npf_to_html():
    """Test the npf_to_html function."""

    # Test cases from Tumblr docs: 1

    content = [
        ContentBlock.from_dict(c)
        for c in [
            {"type": "text", "subtype": "heading1", "text": "Sward's Shopping List"},
            {
                "type": "text",
                "subtype": "ordered-list-item",
                "text": "First level: Fruit",
            },
            {
                "type": "text",
                "subtype": "unordered-list-item",
                "text": "Second level: Apples",
                "indent_level": 1,
            },
            {
                "type": "text",
                "subtype": "ordered-list-item",
                "text": "Third level: Green",
                "indent_level": 2,
            },
            {
                "type": "text",
                "subtype": "unordered-list-item",
                "text": "Second level: Pears",
                "indent_level": 1,
            },
            {
                "type": "text",
                "subtype": "ordered-list-item",
                "text": "First level: Vegetables",
            },
        ]
    ]
    html = npf_to_html(content=content, layouts=[])
    assert (
        html
        == '<div class="text-block"><h1>Sward\'s Shopping List</h1></div><ol class="text-list"><li>First level: Fruit</li><li><ul class="text-list"><li>Second level: Apples</li><li><ol class="text-list"><li>Third level: Green</li></ol></li><li>Second level: Pears</li></ul></li><li>First level: Vegetables</li></ol>'
    )

    content = [
        ContentBlock.from_dict(c)
        for c in [
            {
                "type": "text",
                "subtype": "indented",
                "text": "1: blockquote, not nested",
            },
            {
                "type": "text",
                "subtype": "indented",
                "text": "2: blockquote, nested",
                "indent_level": 1,
            },
            {
                "type": "text",
                "subtype": "unordered-list-item",
                "text": "3: nested in two blockquotes",
                "indent_level": 2,
            },
            {
                "type": "text",
                "subtype": "ordered-list-item",
                "text": "4: nested in two blockquotes and a list",
                "indent_level": 3,
            },
            {
                "type": "text",
                "subtype": "unordered-list-item",
                "text": "3: back to level 3, double nesting",
                "indent_level": 2,
            },
            {
                "type": "text",
                "subtype": "indented",
                "text": "1: back to level 1, no nesting",
            },
        ]
    ]
    html = npf_to_html(content=content, layouts=[])
    assert (
        html
        == '<blockquote class="text-block text-indented"><p>1: blockquote, not nested</p><blockquote class="text-block text-indented"><p>2: blockquote, nested</p><ul class="text-list"><li>3: nested in two blockquotes</li><li><ol class="text-list"><li>4: nested in two blockquotes and a list</li></ol></li><li>3: back to level 3, double nesting</li></ul></blockquote><p>1: back to level 1, no nesting</p></blockquote>'
    )


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
        (
            {
                "type": "image",
                "media": [
                    {
                        "media_key": "1cc6f410b3bc53161f8fbd64d2b28b5a:5b2682c6837efa16-ae",
                        "type": "image/png",
                        "width": 560,
                        "height": 200,
                        "url": 'https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/"5b2682c6837efa16-ae/s640x960/ce8b82f18f36f7b124d718d21442714022a290aa.png',
                        "has_original_dimensions": True,
                    },
                ],
                "alt_text": "<script>alert(1)</script>",
                "attribution": {
                    "type": "link",
                    "url": 'https://example.com/"/><script>alert(2)</script>',
                },
            },
            '<figure class="tmblr-full"><img src="https://64.media.tumblr.com/1cc6f410b3bc53161f8fbd64d2b28b5a/%225b2682c6837efa16-ae/s640x960/ce8b82f18f36f7b124d718d21442714022a290aa.png"/><span class="tmblr-alt-text-helper">ALT</span></figure><div class="attribution image-attribution"><a href="https://example.com/%22/%3E%3Cscript%3Ealert%282%29%3C/script%3E">example.com</a><span class="attribution-go-icon"><svg xmlns="http://www.w3.org/2000/svg" height="14" width="14" role="presentation"><use href="#managed-icon__caret-fat"></use></svg></span></div>',
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
        (
            {
                "type": "link",
                "url": "https://tumblr.com",
                "display_url": "https://tumblr.com",
            },
            '<div class="link-embed"><div class="link-embed-top"><span class="link-title">https://tumblr.com</span></div><div class="link-embed-bottom"></div></div>',
        ),
        (
            {
                "type": "link",
                "url": 'https://example.com/"/><script>alert(1)</script>',
                "display_url": 'https://example.com/"/><script>alert(2)</script>',
                "title": "<script>alert(3)</script>",
                "description": "<script>alert(4)</script>",
                "site_name": "<script>alert(5)</script>",
            },
            '<div class="link-embed"><div class="link-embed-top"><span class="link-title">&lt;script&gt;alert(3)&lt;/script&gt;</span></div><div class="link-embed-bottom"><span class="link-description">&lt;script&gt;alert(4)&lt;/script&gt;</span><span class="link-sitename">&lt;script&gt;alert(5)&lt;/script&gt;</span></div></div>',
        ),
        (
            {
                "type": "link",
                "url": "https://href.li/?https://www.nytimes.com/2017/06/15/us/politics/secrecy-surrounding-senate-health-bill-raises-alarms-in-both-parties.html",
                "display_url": "https://href.li/?https://www.nytimes.com/2017/06/15/us/politics/secrecy-surrounding-senate-health-bill-raises-alarms-in-both-parties.html",
                "title": "Secrecy Surrounding Senate Health Bill Raises Alarms in Both Parties (Published 2017)",
                "description": "Senate leaders are writing legislation to repeal and replace the Affordable Care Act without a single hearing on the bill and without an ope",
                "site_name": "nytimes.com",
                "poster": [
                    {
                        "media_key": "85955a73a8c5d39a74f5c53e5402f342:5b2682c6837efa16-fa",
                        "type": "image/jpeg",
                        "width": 1050,
                        "height": 549,
                        "url": "https://64.media.tumblr.com/85955a73a8c5d39a74f5c53e5402f342/5b2682c6837efa16-fa/s1280x1920/bac3d2656327f6b379e17183b472c86a428e5f4b.jpg",
                    }
                ],
            },
            '<div class="link-embed"><div class="link-embed-image-top"><img src="https://64.media.tumblr.com/85955a73a8c5d39a74f5c53e5402f342/5b2682c6837efa16-fa/s1280x1920/bac3d2656327f6b379e17183b472c86a428e5f4b.jpg" class="link-image"><span class="link-image-title">Secrecy Surrounding Senate Health Bill Raises Alarms in Both Parties (Published 2017)</span></div><div class="link-embed-bottom"><span class="link-description">Senate leaders are writing legislation to repeal and replace the Affordable Care Act without a single hearing on the bill and without an ope</span><span class="link-sitename">nytimes.com</span></div></div>',
        ),
        (
            {
                "type": "link",
                "url": 'https://example.com/"/><script>alert(1)</script>',
                "display_url": 'https://example.com/"/><script>alert(2)</script>',
                "title": "<script>alert(3)</script>",
                "description": "<script>alert(4)</script>",
                "site_name": "<script>alert(5)</script>",
                "poster": [
                    {
                        "media_key": "85955a73a8c5d39a74f5c53e5402f342:5b2682c6837efa16-fa",
                        "type": "image/jpeg",
                        "width": 1050,
                        "height": 549,
                        "url": 'https://64.media.tumblr.com/85955a73a8c5d39a74f5c53e5402f342/"5b2682c6837efa16-fa/s1280x1920/bac3d2656327f6b379e17183b472c86a428e5f4b.jpg',
                    }
                ],
            },
            '<div class="link-embed"><div class="link-embed-image-top"><img src="https://64.media.tumblr.com/85955a73a8c5d39a74f5c53e5402f342/%225b2682c6837efa16-fa/s1280x1920/bac3d2656327f6b379e17183b472c86a428e5f4b.jpg" class="link-image"><span class="link-image-title">&lt;script&gt;alert(3)&lt;/script&gt;</span></div><div class="link-embed-bottom"><span class="link-description">&lt;script&gt;alert(4)&lt;/script&gt;</span><span class="link-sitename">&lt;script&gt;alert(5)&lt;/script&gt;</span></div></div>',
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
            '<figure class="tmblr-full video-block"><img class="video-poster" src="https://64.media.tumblr.com/tumblr_s2dhynoXj51yk47jo_frame1.jpg"/><span class="tmblr-play-button-helper"><svg xmlns="http://www.w3.org/2000/svg" height="32" width="32" role="presentation" style="--icon-color-primary: RGB(255, 255, 255);"><use href="#managed-icon__play-cropped"></use></svg></span></figure>',
        ),
        (
            {
                "type": "video",
                "provider": "youtube",
                "url": "https://www.youtube.com/watch?v=9sPthPleEKo",
                "embed_html": '<iframe width="356" height="200"  id="youtube_iframe" src="https://www.youtube.com/embed/9sPthPleEKo?feature=oembed&amp;enablejsapi=1&amp;origin=https://safe.txmblr.com&amp;wmode=opaque" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen title="Road work ahead? Uh yeah, I sure hope it does [Drew Gooden]"></iframe>',
                "poster": [
                    {
                        "media_key": "3f2bc691a34a4717874cb8525f5bf75e:5b2682c6837efa16-be",
                        "type": "image/jpeg",
                        "width": 480,
                        "height": 360,
                        "url": "https://64.media.tumblr.com/3f2bc691a34a4717874cb8525f5bf75e/5b2682c6837efa16-be/s500x750/ab21befaf02dec37e0f5fbb2d76cf8a6be90a140.jpg",
                    }
                ],
                "embed_iframe": {
                    "url": "https://safe.txmblr.com/svc/embed/inline/https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D9sPthPleEKo#embed-68e9480c0717e466720385",
                    "width": 356,
                    "height": 200,
                },
                "metadata": {"id": "9sPthPleEKo"},
                "attribution": {
                    "type": "app",
                    "app_name": "YouTube",
                    "url": "https://www.youtube.com/watch?v=9sPthPleEKo",
                    "display_text": "? - Road work ahead? Uh yeah, I sure hope it does [Drew Gooden]",
                },
            },
            '<figure class="tmblr-full video-block"><img class="video-poster" src="https://64.media.tumblr.com/3f2bc691a34a4717874cb8525f5bf75e/5b2682c6837efa16-be/s500x750/ab21befaf02dec37e0f5fbb2d76cf8a6be90a140.jpg"/><span class="tmblr-play-button-helper"><svg xmlns="http://www.w3.org/2000/svg" height="32" width="32" role="presentation" style="--icon-color-primary: RGB(255, 255, 255);"><use href="#managed-icon__play-cropped"></use></svg></span></figure><div class="attribution app-attribution"><a href="https://www.youtube.com/watch?v=9sPthPleEKo">YouTube | ? - Road work ahead? Uh yeah, I sure hope it does [Drew Gooden]</a><span class="attribution-go-icon"><svg xmlns="http://www.w3.org/2000/svg" height="14" width="14" role="presentation"><use href="#managed-icon__caret-fat"></use></svg></span></div>',
        ),
        (
            {
                "type": "video",
                "provider": "vimeo",
                "url": "https://vimeo.com/823545557",
                "embed_html": '<iframe src="https://player.vimeo.com/video/823545557?title=0&amp;byline=0&amp;portrait=0&amp;app_id=122963" width="540" height="304" frameborder="0" allow="autoplay; fullscreen; picture-in-picture" title="underscores - Cops and robbers"></iframe>',
                "poster": [
                    {
                        "media_key": "d4d14589e1383ee16f3eae38abb72cb4:5b2682c6837efa16-28",
                        "type": "image/jpeg",
                        "width": 295,
                        "height": 166,
                        "url": "https://64.media.tumblr.com/d4d14589e1383ee16f3eae38abb72cb4/5b2682c6837efa16-28/s400x600/0f95e805ab8aea92372d3fa350b49700bbb13cef.jpg",
                    }
                ],
                "embed_iframe": {
                    "url": "https://safe.txmblr.com/svc/embed/inline/https%3A%2F%2Fvimeo.com%2F823545557#embed-68e9480c07485832543369",
                    "width": 540,
                    "height": 324,
                },
                "attribution": {
                    "type": "app",
                    "app_name": "Vimeo",
                    "url": "https://vimeo.com/823545557",
                    "display_text": "Ayodeji - underscores - Cops and robbers",
                },
            },
            '<figure class="tmblr-full video-block"><img class="video-poster" src="https://64.media.tumblr.com/d4d14589e1383ee16f3eae38abb72cb4/5b2682c6837efa16-28/s400x600/0f95e805ab8aea92372d3fa350b49700bbb13cef.jpg"/><span class="tmblr-play-button-helper"><svg xmlns="http://www.w3.org/2000/svg" height="32" width="32" role="presentation" style="--icon-color-primary: RGB(255, 255, 255);"><use href="#managed-icon__play-cropped"></use></svg></span></figure><div class="attribution app-attribution"><a href="https://vimeo.com/823545557">Vimeo | Ayodeji - underscores - Cops and robbers</a><span class="attribution-go-icon"><svg xmlns="http://www.w3.org/2000/svg" height="14" width="14" role="presentation"><use href="#managed-icon__caret-fat"></use></svg></span></div>',
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
            '<div class="audio-player audio-tumblr"><div class="play-button"><svg xmlns="http://www.w3.org/2000/svg" height="24" width="24" role="presentation" style="--icon-color-primary: RGB(var(--white));"><use href="#managed-icon__play-cropped"></use></svg></div><div class="audio-info"><div class="title">Example Track</div><div class="artist">Example Artist</div><div class="album">Example Album</div></div><div class="audio-image"><img src="https://64.media.tumblr.com/41023f06513343104e9520f824c44c95/5b2682c6837efa16-2a/s250x400/daf29fc6b4c169a4b8513dc09321c2340f6d5311.jpg"></div></div>',
        ),
        (
            {
                "type": "audio",
                "provider": "tumblr",
                "url": 'https://64.media.tumblr.com/58138b56a8729251b81de4f6d401d2a9/"86e7573156aa2ff2-29/651608e8278b463944dc2f22bae0bcf3a7f0ef62.mp3',
                "title": "<script>alert(1)</script>",
                "artist": "<script>alert(2)</script>",
                "album": "<script>alert(3)</script>",
                "media": {
                    "media_key": "58138b56a8729251b81de4f6d401d2a9:5b2682c6837efa16-ea",
                    "type": "audio/mpeg",
                    "url": 'https://64.media.tumblr.com/58138b56a8729251b81de4f6d401d2a9/"5b2682c6837efa16-ea/afe1a484a9c04fc15702c8ce9bdb1807d6631a94.mp3',
                },
                "poster": [
                    {
                        "media_key": "41023f06513343104e9520f824c44c95:5b2682c6837efa16-2a",
                        "type": "image/jpeg",
                        "width": 170,
                        "height": 258,
                        "url": 'https://64.media.tumblr.com/41023f06513343104e9520f824c44c95/"5b2682c6837efa16-2a/s250x400/daf29fc6b4c169a4b8513dc09321c2340f6d5311.jpg',
                    }
                ],
            },
            '<div class="audio-player audio-tumblr"><div class="play-button"><svg xmlns="http://www.w3.org/2000/svg" height="24" width="24" role="presentation" style="--icon-color-primary: RGB(var(--white));"><use href="#managed-icon__play-cropped"></use></svg></div><div class="audio-info"><div class="title">&lt;script&gt;alert(1)&lt;/script&gt;</div><div class="artist">&lt;script&gt;alert(2)&lt;/script&gt;</div><div class="album">&lt;script&gt;alert(3)&lt;/script&gt;</div></div><div class="audio-image"><img src="https://64.media.tumblr.com/41023f06513343104e9520f824c44c95/%225b2682c6837efa16-2a/s250x400/daf29fc6b4c169a4b8513dc09321c2340f6d5311.jpg"></div></div>',
        ),
    )

    for data, expected_result in examples:
        block = ContentBlockAudio.from_dict(data)
        assert isinstance(block, ContentBlockAudio)
        assert block.to_html() == expected_result


async def test_block_poll(tumblr_api):
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
                "_fxt_test_data": {"blog": "knuxify", "post": 730903802869317632},
            },
            '<div class="poll-block poll-over"><span class="poll-question">A poll!</span><div class="poll-answer poll-answer-win"><div class="poll-answer-filler" style="width: 50%;"></div><span class="poll-answer-text">I love NPF!</span><span class="poll-answer-percentage">50%</span></div><div class="poll-answer poll-answer-win"><div class="poll-answer-filler" style="width: 50%;"></div><span class="poll-answer-text">Why must thou do this to me, Tumblr.</span><span class="poll-answer-percentage">50%</span></div><span class="poll-meta">Final result</span></div>',
        ),
        (
            {
                "type": "poll",
                "client_id": "e040d07a-ca6a-4751-8df5-ebaa1719222e",
                "question": "<script>alert(1)</script>",
                "answers": [
                    {
                        "client_id": "0e094aec-5f4a-42c3-aa5f-4dc79cebabe7",
                        "answer_text": "<script>alert(2)</script>",
                    },
                    {
                        "client_id": "3fd6cbc9-a929-4a71-a9ea-945fc2bceee3",
                        "answer_text": "<script>alert(3)</script>",
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
                "_fxt_test_data": {"blog": "knuxify", "post": 730903802869317632},
            },
            '<div class="poll-block poll-over"><span class="poll-question">&lt;script&gt;alert(1)&lt;/script&gt;</span><div class="poll-answer poll-answer-win"><div class="poll-answer-filler" style="width: 50%;"></div><span class="poll-answer-text">&lt;script&gt;alert(2)&lt;/script&gt;</span><span class="poll-answer-percentage">50%</span></div><div class="poll-answer poll-answer-win"><div class="poll-answer-filler" style="width: 50%;"></div><span class="poll-answer-text">&lt;script&gt;alert(3)&lt;/script&gt;</span><span class="poll-answer-percentage">50%</span></div><span class="poll-meta">Final result</span></div>',
        ),
    )

    for data, expected_result in examples:
        block = ContentBlockPoll.from_dict(data)
        assert isinstance(block, ContentBlockPoll)
        await block.fetch_results(
            tumblr_api,
            data["_fxt_test_data"]["blog"],
            data["_fxt_test_data"]["post"],
            skip_cache=True,
        )
        assert block.to_html() == expected_result
