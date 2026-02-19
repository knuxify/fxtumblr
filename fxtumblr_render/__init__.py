# SPDX-License-Identifier: MIT
"""Renderer server code."""

import os

from fxtumblr.config_parser import Config

if "PYTEST_CURRENT_TEST" not in os.environ:
    config = Config.from_file("config.toml")
