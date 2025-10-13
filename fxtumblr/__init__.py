# SPDX-License-Identifier: MIT
"""fxtumblr - fix Tumblr embeds on other websites."""

import tomllib
from logging import getLogger

with open("config.toml", "rb") as config_file:
    config = tomllib.load(config_file)

logger = getLogger("fxtumblr")
