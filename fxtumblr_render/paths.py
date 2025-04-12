"""
Path generators. Render paths need to follow a specific format to
allow for stacking modifiers:

{render path}/{blog name}-{id}.{comma,separated,modifiers}.{extension}

where modifiers are sorted alphabetically.
"""

import os
from fxtumblr.config import config
from typing import Optional

RENDERS_PATH = config["renders_path"]

VALID_MODIFIERS = ("dark", "unroll", "oldstyle")


def filename_for(
    blogname: str, post_id: int, extension: str, modifiers: Optional[list[str]] = None
) -> str:
    """Generates a render path with the given data."""
    if modifiers:
        for mod in modifiers:
            if mod not in VALID_MODIFIERS:
                raise ValueError(f"Invalid modifier {mod}")
        return f"{blogname}-{post_id}.{','.join(sorted(modifiers))}.{extension}"
    return f"{blogname}-{post_id}.{extension}"


def path_to(
    blogname: str, post_id: int, extension: str, modifiers: Optional[list[str]] = None
) -> str:
    """Shorthand for RENDERS_PATH + filename_for..."""
    return os.path.join(
        RENDERS_PATH,
        filename_for(
            blogname=blogname, post_id=post_id, extension=extension, modifiers=modifiers
        ),
    )


def from_filename(filename: str) -> dict:
    """
    Splits a render filename into its individual components.
    Returns a dict with blogname, post_id, modifiers and extension fields.
    Raises ValueError if the filename is incorrect.
    """
    try:
        blogname, delim, rest = filename.rpartition("-")
        if rest.count(".") == 2:
            post_id, modifiers, extension = rest.split(".")
            modifiers = sorted(modifiers.split(","))
        elif rest.count(".") == 1:
            post_id, extension = rest.split(".")
            modifiers = []
        else:
            raise ValueError
        for mod in modifiers:
            if mod not in VALID_MODIFIERS:
                raise ValueError(f"Invalid modifier {mod}")
    except ValueError as e:
        raise ValueError("Malformed filename") from e

    return {
        "blogname": blogname,
        "post_id": post_id,
        "extension": extension,
        "modifiers": modifiers,
    }


def normalize_filename(filename: str) -> str:
    """Returns a normalized filename."""
    split = from_filename(filename)
    return filename_for(
        blogname=split["blogname"],
        post_id=split["post_id"],
        extension=split["extension"],
        modifiers=split["modifiers"],
    )
