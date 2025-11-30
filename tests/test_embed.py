# SPDX-License-Identifier: MIT
"""Test embed generation code."""

from markupsafe import Markup

from fxtumblr.embed import Embed


def test_embed_class():
    """Test the Embed class."""

    embed = Embed(title="test")

    assert embed.to_meta_tags() == Markup(
        '<meta property="twitter:card" content="summary_large_image""/><meta property="og:title" content="test"/><meta property="twitter:title" content="test"/>'
    )
    assert embed.to_oembed() == {"version": "1.0", "type": "link", "title": "test"}
    assert (
        embed.to_oembed_url()
        == "https://example.com/_api/oembed.json?type=link&title=test"
    )
    assert embed.to_meta_tags(oembed_link=True) == Markup(
        '<meta property="twitter:card" content="summary_large_image""/><meta property="og:title" content="test"/><meta property="twitter:title" content="test"/><link rel="alternate" type="application/json+oembed" href="https://example.com/_api/oembed.json?type=link&amp;title=test"/>'
    )

    embed = Embed(title='"test?')
    assert embed.to_meta_tags() == Markup(
        '<meta property="twitter:card" content="summary_large_image""/><meta property="og:title" content="&#34;test?"/><meta property="twitter:title" content="&#34;test?"/>'
    )
    assert (
        embed.to_oembed_url()
        == "https://example.com/_api/oembed.json?type=link&title=%22test%3F"
    )
    assert embed.to_meta_tags(oembed_link=True) == Markup(
        '<meta property="twitter:card" content="summary_large_image""/><meta property="og:title" content="&#34;test?"/><meta property="twitter:title" content="&#34;test?"/><link rel="alternate" type="application/json+oembed" href="https://example.com/_api/oembed.json?type=link&amp;title=%22test%3F"/>'
    )
