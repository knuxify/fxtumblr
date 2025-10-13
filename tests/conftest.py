# SPDX-License-Identifier: MIT
"""Test configuration and fixtures for fxtumblr tests."""

import json
import logging
import os
from inspect import getsourcefile

import pytest

import fxtumblr.app
from fxtumblr.tumblr.api import TumblrAPI

# Override the default logger
fxtumblr.app.logger = logging.Logger(__name__)


def _get_tumblr_test_data(filename: str) -> os.PathLike:
    """Get the path to a file in tumblr/test_data."""
    # https://stackoverflow.com/a/18489147
    return os.path.join(
        os.path.dirname(os.path.abspath(getsourcefile(lambda: 0))),
        "tumblr",
        "test_data",
        filename,
    )


@pytest.fixture
def tumblr_api_server(httpserver):
    """Test fixture that simulates Tumblr's API."""

    # Test post 1: Ultimate NPF Test Post
    # https://www.tumblr.com/knuxify/730903802869317632/the-ultimate-test-post-v2
    with open(_get_tumblr_test_data("post_npftest.json")) as test_data:
        httpserver.expect_request(
            "/blog/knuxify/posts",
            query_string={
                "id": "730903802869317632",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Test post 2: Random reblog chain
    # https://www.tumblr.com/punkitt-is-here/781681205274886144
    with open(_get_tumblr_test_data("post_reblogs.json")) as test_data:
        httpserver.expect_request(
            "/blog/punkitt-is-here/posts",
            query_string={
                "id": "781681205274886144",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Result of post_id=0
    with open(_get_tumblr_test_data("post_id0.json")) as test_data:
        httpserver.expect_request(
            "/blog/knuxify/posts",
            query_string={"id": "0", "npf": "true", "api_key": "consumer_key"},
        ).respond_with_json(json.load(test_data))

    with open(_get_tumblr_test_data("resp_404.json")) as test_data:
        httpserver.expect_request(
            "/blog/a/posts",
        ).respond_with_json(json.load(test_data), status=404)

        test_data.seek(0)
        httpserver.expect_request(
            "/blog/knuxify/posts",
            query_string={"id": "1234", "npf": "true", "api_key": "consumer_key"},
        ).respond_with_json(json.load(test_data), status=404)

    return httpserver


@pytest.fixture
def tumblr_api(tumblr_api_server):
    """
    Fixture providing TumblrAPI object.

    If a consumer key and secret are provided using environment variables,
    the tests will attempt to connect to the real Tumblr servers; if not,
    a simulated API server will be provided.
    """
    consumer_key = os.environ.get("FXTUMBLR_TEST_TUMBLR_KEY")
    consumer_secret = os.environ.get("FXTUMBLR_TEST_TUMBLR_SECRET")

    if consumer_key and consumer_key:
        t = TumblrAPI(consumer_key, consumer_secret)
    else:
        t = TumblrAPI("consumer_key", "consumer_secret")
        t.api_base = tumblr_api_server.url_for("/")

    return t
