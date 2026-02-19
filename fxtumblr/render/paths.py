# SPDX-License-Identifier: MIT
"""Functions for dealing with render paths and URLs."""

import os.path
import re

from .. import config
from . import RenderFiletype, RenderModifier


def get_modifier_string(modifiers: list[RenderModifier]):
    """Convert a list of modifiers to an ordered modifier string."""
    modifier_strings = []

    for mod in modifiers:
        try:
            modifier_strings.append(str(RenderModifier(mod)))
        except ValueError:  # not a valid modifier
            pass

    return ",".join(sorted(modifier_strings))


# Path functions


def get_render_path(
    blog_name: str,
    post_id: int,
    modifiers: list[RenderModifier] | None = None,
    filetype: RenderFiletype = RenderFiletype.PNG,
) -> str:
    """
    Return the path to the render PNG for the given parameters.

    :param blog_name: Blog name of post author.
    :param post_id: ID of post.
    :param modifiers: List of modifiers to apply to the render.
    :param filetype: File type of the returned render.
    :returns: The full path to the render.
    :raises ValueError: if the blog ID or post ID are invalid.
    """
    if modifiers is None:
        modifiers = []

    # Modifier string is guaranteed to be path-safe as only specific strings
    # are allowed
    modifier_str = get_modifier_string(modifiers)

    # Blog name is guaranteed to be path-safe for legitimate posts (blog names
    # cannot contain slashes or dots), but make sure it's OK just in case
    if not re.match(r"^[a-zA-Z0-9\-]*$", blog_name):
        raise ValueError("Invalid blog ID")

    if not isinstance(post_id, int):
        raise ValueError("Invalid post ID")

    filename = f"{blog_name}_{post_id}_{modifier_str}.{str(filetype)}"

    return os.path.join(config["render"]["path"], filename)


# URL functions


def get_render_url(
    blog_name: str,
    post_id: int,
    modifiers: list[RenderModifier] | None = None,
    filetype: RenderFiletype = RenderFiletype.PNG,
) -> str:
    """
    Return the URL to the render PNG for the given parameters.

    :param blog_name: Blog name of post.
    :param post_id: ID of post.
    :param modifiers: List of modifiers to apply to the render.
    :param filetype: File type of the returned render.
    :returns: The user-facing URL to the render PNG.
    """
    if modifiers is None:
        modifiers = []

    modifier_str = get_modifier_string(modifiers)

    return (
        "https://"
        + config["instance"]["domain"]
        + f"/_api/render/{blog_name}/{post_id}/render.{modifier_str}.{str(filetype)}"
    )
