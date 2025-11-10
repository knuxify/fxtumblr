# SPDX-License-Identifier: MIT
"""Test embed generation code."""

from fxtumblr.embed import Embed


def test_embed_class():
    """Test the Embed class."""

    embed = Embed(title="test")

    assert (
        embed.to_meta_tags()
        == '<meta property="og:title" content="test"/><meta property="twitter:title" content="test"/>'
    )
    assert embed.to_oembed() == {"version": "1.0", "type": "link", "title": "test"}
    assert (
        embed.to_oembed_url()
        == "https://example.com/_api/oembed.json?type=link&title=test"
    )
    assert (
        embed.to_meta_tags(oembed_link=True)
        == '<meta property="og:title" content="test"/><meta property="twitter:title" content="test"/><link rel="alternate" type="application/json+oembed" href="https://example.com/_api/oembed.json?type=link&title=test"/>'
    )

    embed = Embed(title='"test?')
    assert (
        embed.to_meta_tags()
        == '<meta property="og:title" content="&quot;test?"/><meta property="twitter:title" content="&quot;test?"/>'
    )
    assert (
        embed.to_oembed_url()
        == "https://example.com/_api/oembed.json?type=link&title=%22test%3F"
    )
    assert (
        embed.to_meta_tags(oembed_link=True)
        == '<meta property="og:title" content="&quot;test?"/><meta property="twitter:title" content="&quot;test?"/><link rel="alternate" type="application/json+oembed" href="https://example.com/_api/oembed.json?type=link&title=%22test%3F"/>'
    )
