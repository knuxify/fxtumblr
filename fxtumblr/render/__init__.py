# SPDX-License-Identifier
"""Code for interfacing with the renderer."""

from enum import StrEnum


class RenderModifier(StrEnum):
    """Render modifiers."""

    DARK = "dark"
    UNROLL = "unroll"
    DATE = "date"


class RenderFiletype(StrEnum):
    """Filetypes for the render."""

    PNG = "png"
    HTML = "html"


RENDER_FILETYPE_MIMES: dict[RenderFiletype, str] = {
    RenderFiletype.PNG: "image/png",
    RenderFiletype.HTML: "text/html",
}
