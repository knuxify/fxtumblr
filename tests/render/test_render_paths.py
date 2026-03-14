# SPDX-License-Identifier: MIT
"""Tests for the fxtumblr.render.paths module."""

import pytest

from fxtumblr.render import RenderFiletype, RenderModifier
from fxtumblr.render.paths import (
    decode_legacy_filename,
    get_modifier_list,
    get_modifier_string,
    get_render_cache_key,
    get_render_path,
    get_render_url,
)


def test_modifier_string():
    """Test modifier string functions."""

    # Empty list
    assert get_modifier_string([]) == ""

    # Order/sorting
    assert (
        get_modifier_string([RenderModifier.DARK, RenderModifier.UNROLL])
        == "dark,unroll"
    )
    assert (
        get_modifier_string([RenderModifier.UNROLL, RenderModifier.DARK])
        == "dark,unroll"
    )

    # Deduplication
    assert (
        get_modifier_string(
            [RenderModifier.UNROLL, RenderModifier.DARK, RenderModifier.DARK]
        )
        == "dark,unroll"
    )

    # Invalid values
    with pytest.raises(ValueError):
        get_modifier_string(["a", 1, True])  # type: ignore[invalid-argument-type]

    assert (
        get_modifier_string(["a", 1, True, RenderModifier.DARK], ignore_invalid=True)  # type: ignore[invalid-argument-type]
        == "dark"
    )
    assert get_modifier_string(["a", 1, True], ignore_invalid=True) == ""  # type: ignore[invalid-argument-type]


def test_modifier_list():
    """Test modifier list functions."""

    # Empty list
    assert get_modifier_list("") == []

    # Order
    assert set(get_modifier_list("dark,unroll")) == {
        RenderModifier.DARK,
        RenderModifier.UNROLL,
    }
    assert set(get_modifier_list("unroll,dark")) == {
        RenderModifier.DARK,
        RenderModifier.UNROLL,
    }

    # Deduplication
    assert set(get_modifier_list("unroll,dark,dark")) == {
        RenderModifier.DARK,
        RenderModifier.UNROLL,
    }

    # Invalid values
    with pytest.raises(ValueError):
        get_modifier_list("a,b,c")

    assert get_modifier_list("a,b,dark", ignore_invalid=True) == [RenderModifier.DARK]
    assert get_modifier_list("a,b,c", ignore_invalid=True) == []


def test_render_url():
    """Test the render URL generation function."""

    assert (
        get_render_url("knuxify", 1234, modifiers=None, filetype=RenderFiletype.PNG)
        == "https://example.com/_api/renders/post/knuxify/1234/render.png"
    )

    assert (
        get_render_url("knuxify", 1234, modifiers=None, filetype=RenderFiletype.HTML)
        == "https://example.com/_api/renders/post/knuxify/1234/render.html"
    )

    assert (
        get_render_url(
            "knuxify",
            1234,
            modifiers=[RenderModifier.UNROLL],
            filetype=RenderFiletype.PNG,
        )
        == "https://example.com/_api/renders/post/knuxify/1234/render.png?modifiers=unroll"
    )

    assert (
        get_render_url(
            "knuxify",
            1234,
            modifiers=[RenderModifier.DARK, RenderModifier.UNROLL],
            filetype=RenderFiletype.PNG,
        )
        == "https://example.com/_api/renders/post/knuxify/1234/render.png?modifiers=dark,unroll"
    )
    assert (
        get_render_url(
            "knuxify",
            1234,
            modifiers=[RenderModifier.UNROLL, RenderModifier.DARK],
            filetype=RenderFiletype.PNG,
        )
        == "https://example.com/_api/renders/post/knuxify/1234/render.png?modifiers=dark,unroll"
    )

    assert (
        get_render_url("knuxify", 1234, modifiers=[], filetype=RenderFiletype.PNG)
        == "https://example.com/_api/renders/post/knuxify/1234/render.png"
    )


def test_render_path():
    """Test the render path generation function."""

    assert (
        get_render_path("knuxify", 1234, modifiers=None, filetype=RenderFiletype.PNG)
        == "/path/to/renders/knuxify_1234.png"
    )

    assert (
        get_render_path("knuxify", 1234, modifiers=None, filetype=RenderFiletype.HTML)
        == "/path/to/renders/knuxify_1234.html"
    )

    assert (
        get_render_path(
            "knuxify",
            1234,
            modifiers=[RenderModifier.UNROLL],
            filetype=RenderFiletype.PNG,
        )
        == "/path/to/renders/knuxify_1234_unroll.png"
    )

    assert (
        get_render_path(
            "knuxify",
            1234,
            modifiers=[RenderModifier.DARK, RenderModifier.UNROLL],
            filetype=RenderFiletype.PNG,
        )
        == "/path/to/renders/knuxify_1234_dark,unroll.png"
    )
    assert (
        get_render_path(
            "knuxify",
            1234,
            modifiers=[RenderModifier.UNROLL, RenderModifier.DARK],
            filetype=RenderFiletype.PNG,
        )
        == "/path/to/renders/knuxify_1234_dark,unroll.png"
    )

    assert (
        get_render_path("knuxify", 1234, modifiers=[], filetype=RenderFiletype.PNG)
        == "/path/to/renders/knuxify_1234.png"
    )


def test_decode_legacy_filename():
    """Test the legacy filename decode function."""

    blog_name, post_id, modifiers, filetype = decode_legacy_filename("knuxify-1234.png")

    assert blog_name == "knuxify"
    assert post_id == 1234
    assert modifiers == []
    assert filetype == RenderFiletype.PNG

    blog_name, post_id, modifiers, filetype = decode_legacy_filename(
        "knuxify-1234.dark,unroll.png"
    )

    assert blog_name == "knuxify"
    assert post_id == 1234
    assert modifiers == [RenderModifier.DARK, RenderModifier.UNROLL]
    assert filetype == RenderFiletype.PNG

    blog_name, post_id, modifiers, filetype = decode_legacy_filename(
        "knuxify-1234.dark,oldstyle,unroll.png"
    )

    assert blog_name == "knuxify"
    assert post_id == 1234
    assert modifiers == [RenderModifier.DARK, RenderModifier.UNROLL]
    assert filetype == RenderFiletype.PNG

    with pytest.raises(ValueError):
        decode_legacy_filename("knuxify-1234.a,b,c.png")

    with pytest.raises(ValueError):
        decode_legacy_filename("knuxify-1234.asdf")

    with pytest.raises(ValueError):
        decode_legacy_filename("knuxify-abcd.png")


def test_render_cache_key():
    """Test render cache key functions."""
    assert (
        get_render_cache_key(
            "knuxify", 1234, modifiers=None, filetype=RenderFiletype.PNG
        )
        == "fxt-render:post:knuxify:1234::png"
    )

    assert (
        get_render_cache_key(
            "knuxify", 1234, modifiers=None, filetype=RenderFiletype.HTML
        )
        == "fxt-render:post:knuxify:1234::html"
    )

    assert (
        get_render_cache_key(
            "knuxify",
            1234,
            modifiers=[RenderModifier.UNROLL],
            filetype=RenderFiletype.PNG,
        )
        == "fxt-render:post:knuxify:1234:unroll:png"
    )

    assert (
        get_render_cache_key(
            "knuxify",
            1234,
            modifiers=[RenderModifier.DARK, RenderModifier.UNROLL],
            filetype=RenderFiletype.PNG,
        )
        == "fxt-render:post:knuxify:1234:dark,unroll:png"
    )
    assert (
        get_render_cache_key(
            "knuxify",
            1234,
            modifiers=[RenderModifier.UNROLL, RenderModifier.DARK],
            filetype=RenderFiletype.PNG,
        )
        == "fxt-render:post:knuxify:1234:dark,unroll:png"
    )

    assert (
        get_render_cache_key("knuxify", 1234, modifiers=[], filetype=RenderFiletype.PNG)
        == "fxt-render:post:knuxify:1234::png"
    )
