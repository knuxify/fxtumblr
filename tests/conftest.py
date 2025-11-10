# SPDX-License-Identifier: MIT
"""Test configuration and fixtures for fxtumblr tests."""

import json
import os
from inspect import getsourcefile

import pytest

import fxtumblr
import fxtumblr.app
from fxtumblr.tumblr.api import TumblrAPI

# Override the config
fxtumblr.config = {
    "instance": {
        "name": "Example instance",
        "domain": "example.com",
        "motd": ["Test MOTD"],
    },
    "stats": {
        "enabled": False,
    },
}


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

    # Test post 3: Answer to ask
    with open(_get_tumblr_test_data("post_ask.json")) as test_data:
        httpserver.expect_request(
            "/blog/knuxify/posts",
            query_string={
                "id": "732094755733929984",
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

    # Poll results for Ultimate NPF Test Post
    with open(_get_tumblr_test_data("poll_results_npftest.json")) as test_data:
        httpserver.expect_request(
            "/polls/knuxify/730903802869317632/e040d07a-ca6a-4751-8df5-ebaa1719222e/results",
            query_string={
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Poll results: invalid poll ID
    with open(_get_tumblr_test_data("poll_results_invalid_id.json")) as test_data:
        httpserver.expect_request(
            "/polls/knuxify/730903802869317632/bogus/results",
            query_string={
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data), status=400)

    # 404 responses
    with open(_get_tumblr_test_data("resp_404.json")) as test_data:
        data = json.load(test_data)

        httpserver.expect_request(
            "/blog/a/posts",
        ).respond_with_json(data, status=404)

        httpserver.expect_request(
            "/blog/knuxify/posts",
            query_string={"id": "1234", "npf": "true", "api_key": "consumer_key"},
        ).respond_with_json(data, status=404)

        httpserver.expect_request(
            "/polls/knuxify/730903802869317632/f040d07a-ca6a-4751-8df5-ebaa1719222e/results",
            query_string={"api_key": "consumer_key"},
        ).respond_with_json(data, status=404)

        httpserver.expect_request(
            "/polls/knuxify/1234/e040d07a-ca6a-4751-8df5-ebaa1719222e/results",
            query_string={"api_key": "consumer_key"},
        ).respond_with_json(data, status=404)

        httpserver.expect_request(
            "/polls/a/1234/e040d07a-ca6a-4751-8df5-ebaa1719222e/results",
            query_string={"api_key": "consumer_key"},
        ).respond_with_json(data, status=404)

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
