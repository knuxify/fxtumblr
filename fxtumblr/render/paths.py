# SPDX-License-Identifier: MIT
"""Functions for dealing with render paths and URLs."""

import os.path
import re

from .. import config
from . import RenderFiletype, RenderModifier

BLOG_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\-]*$")


def get_modifier_string(
    modifiers: list[RenderModifier], ignore_invalid: bool = False
) -> str:
    """
    Convert a list of modifiers to an ordered modifier string.

    :param modifiers: List of render modifiers.
    :param ignore_invalid: If True, silently ignores invalid modifiers.
    :returns: String representing the modifiers.
    :raises ValueError: if a modifier in the list is invalid and ignore_invalid
                        is False.
    """
    modifier_strings = []

    for mod in modifiers:
        try:
            modifier_strings.append(str(RenderModifier(mod)))
        except ValueError as e:  # not a valid modifier
            if not ignore_invalid:
                raise ValueError(f"Invalid modifier {mod}") from e

    return ",".join(sorted(modifier_strings))


def get_modifier_list(
    modifier_str: str, ignore_invalid: bool = False
) -> list[RenderModifier]:
    """
    Convert a modifier string into a list of modifiers.

    :param modifier_str: Modifier string to convert.
    :param ignore_invalid: If True, silently ignores invalid modifiers.
    :returns: List of render modifiers.
    :raises ValueError: if a modifier in the list is invalid and ignore_invalid
                        is False.
    """
    modifiers = []

    for mod in modifier_str.split(","):
        try:
            modifiers.append(RenderModifier(mod))
        except ValueError as e:  # not a valid modifier
            if not ignore_invalid:
                raise ValueError(f"Invalid modifier {mod}") from e

    return modifiers


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

    # Validate blog name and post ID
    if not BLOG_NAME_REGEX.match(blog_name):
        raise ValueError("Invalid blog ID")

    if not isinstance(post_id, int):
        raise ValueError("Invalid post ID")

    if modifier_str:
        filename = f"{blog_name}_{post_id}_{modifier_str}.{str(filetype)}"
    else:
        filename = f"{blog_name}_{post_id}.{str(filetype)}"

    return os.path.join(config.render.path, filename)


def decode_legacy_filename(
    filename: str,
) -> tuple[str, int, list[RenderModifier], RenderFiletype]:
    """
    Split a legacy render filename (from fxtumblr v1) into the blog name,
    post ID and modifiers.

    :param filename: Filename to parse.
    :returns: Tuple containing blog name, post ID, list of modifiers and filetype.
    :raises ValueError: if the values are invalid.
    """

    # Legacy filenames follow the following format:
    # - No modifiers: blogname-postid.ext
    # - Modifiers: blogname-postid.mod1,mod2.ext

    modifiers: list[RenderModifier] = []

    # rpartition returns everything before the delimeter, the delimeter, and
    # everything after the delimeter.
    blog_name, _, rest = filename.rpartition("-")

    # Validate blog name
    if not BLOG_NAME_REGEX.match(blog_name):
        raise ValueError("Invalid blog name")

    # Two dots means modifiers are present
    if rest.count(".") == 2:
        post_id_str, modifiers_str, extension = rest.split(".")
        for mod in modifiers_str.split(","):
            try:
                modifiers.append(RenderModifier(mod))
            except ValueError as e:  # not a valid modifier
                if mod == "oldstyle":
                    # Undocumented in v1, dropped in v2. Don't break embeds
                    # that used it.
                    pass
                else:
                    raise ValueError(f"Invalid modifier {mod}") from e

    # One dot means no modifiers
    elif rest.count(".") == 1:
        post_id_str, extension = rest.split(".")

    try:
        post_id = int(post_id_str)
    except ValueError as e:
        raise ValueError("Invalid post ID") from e

    try:
        filetype = RenderFiletype(extension)
    except ValueError as e:
        raise ValueError(f"Unknown filetype {extension}") from e

    return (blog_name, post_id, modifiers, filetype)


# URL functions


def get_render_url(
    blog_name: str,
    post_id: int,
    modifiers: list[RenderModifier] | None = None,
    filetype: RenderFiletype = RenderFiletype.PNG,
) -> str:
    """
    Return the URL to the render for the given parameters.

    :param blog_name: Blog name of post.
    :param post_id: ID of post.
    :param modifiers: List of modifiers to apply to the render.
    :param filetype: File type of the returned render.
    :returns: The user-facing URL to the render.
    """
    if modifiers is None:
        modifiers = []

    modifier_str = get_modifier_string(modifiers)

    return (
        "https://"
        + config.instance.domain
        + f"/_api/render/{blog_name}/{post_id}/render.{modifier_str}.{str(filetype)}"
    )


# Miscelaneous


def get_render_cache_key(
    blog_name: str,
    post_id: int,
    modifiers: list[RenderModifier] | None = None,
    filetype: RenderFiletype = RenderFiletype.PNG,
) -> str:
    """
    Return the cache key to the render with the given parameters.

    :param blog_name: Blog name of post.
    :param post_id: ID of post.
    :param modifiers: List of modifiers to apply to the render.
    :param filetype: File type of the returned render.
    :returns: The cache key for the render.
    """
    if modifiers is None:
        modifiers = []

    modifier_str = get_modifier_string(modifiers)

    return f"fxt-render:post:{blog_name}:{post_id}:{modifier_str}:{str(filetype)}"
