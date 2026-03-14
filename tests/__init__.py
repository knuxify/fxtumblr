# SPDX-License-Identifier: MIT
"""Test suite for fxtumblr."""

import os

os.environ["IN_PYTEST"] = "1"

import fxtumblr
from fxtumblr.config_parser import Config

# Override the config
fxtumblr.config = Config.from_data(
    {
        "instance": {
            "name": "Example instance",
            "domain": "example.com",
            "contact_email": "example@example.com",
            "motd": ["Test MOTD"],
        },
        "stats": {
            "enabled": False,
        },
        "tumblr": {"api_keys": [("FIXME", "FIXME")]},
        "redis": {
            "host": "127.0.0.1",
            "port": 9600,
        },
        "render": {
            "host": "127.0.0.1",
            "port": 6500,
            # The following get changed for renderer tests
            "backend": "playwright-chromium",
            "path": "/path/to/renders",
        },
    }
)
