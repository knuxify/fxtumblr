# SPDX-License-Identifier: MIT
"""
Helper functions and definitions for screenshot handling.

Taking screenshots is handled by the browser backends, see browser.py.
"""

from enum import StrEnum


# Screenshot types
class ScreenshotFiletype(StrEnum):
    """Valid screenshot filetypes."""

    PNG = "png"
    JPG = "jpg"
    WEBP = "webp"
