# SPDX-License-Identifier: MIT
"""Functions for dealing with render paths and URLs."""

from .. import config
from . import RenderModifier


def get_modifier_string(modifiers: list[RenderModifier]):
    """Convert a list of modifiers to an ordered modifier string."""
    modifier_strings = []

    for mod in modifiers:
        try:
            modifier_strings.append(str(RenderModifier(mod)))
        except ValueError:  # not a valid modifier
            pass

    return ",".join(sorted(modifier_strings))


# URL functions


def get_render_url(
    blog_name: str, post_id: int, modifiers: list[RenderModifier] | None = None
) -> str:
    """
    Return the URL to the render PNG for the given parameters.

    :param blog_name: Blog name of post.
    :param post_id: ID of post.
    :param modifiers: List of modifiers to apply to the render.
    :returns: The user-facing URL to the render PNG.
    """
    if modifiers is None:
        modifiers = []

    modifier_str = get_modifier_string(modifiers)

    return (
        "https://"
        + config["instance"]["domain"]
        + f"/_api/render/{blog_name}/{post_id}/render.{modifier_str}.png"
    )
