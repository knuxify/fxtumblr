# SPDX-License-Identifier: MIT
"""Test suite for fxtumblr."""

import fxtumblr

# Override the config
fxtumblr.config = {
    "instance": {
        "name": "Example instance",
        "domain": "example.com",
        "contact_email": "example@example.com",
        "motd": ["Test MOTD"],
    },
    "stats": {
        "enabled": False,
    },
    "tumblr": {
        "consumer_key": "FIXME",
        "consumer_secret": "FIXME",
    },
    "redis": {
        "host": "127.0.0.1",
        "port": 9600,
    },
}
