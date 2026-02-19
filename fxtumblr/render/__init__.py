# SPDX-License-Identifier
"""
Code for interfacing with renders. For the renderer server, see the
fxtumblr_render module.
"""

from enum import StrEnum


class RenderModifier(StrEnum):
    """Render modifiers."""

    DARK = "dark"
    UNROLL = "unroll"


class RenderFiletype(StrEnum):
    """Filetypes for the render."""

    PNG = "png"
    HTML = "html"
