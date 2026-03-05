# SPDX-License-Identifier: MIT
"""fxtumblr - fix Tumblr embeds on other websites."""

import os
from logging import getLogger

from .config_parser import Config

if "PYTEST_CURRENT_TEST" not in os.environ and "IN_PYTEST" not in os.environ:
    config = Config.from_file("config.toml")

logger = getLogger("fxtumblr")
