# SPDX-License-Identifier: MIT
"""Test configuration and fixtures for fxtumblr tests."""

import json
import os
from inspect import getsourcefile

import pytest

os.environ["IN_PYTEST"] = "1"

from fxtumblr.tumblr.api import TumblrAPI


def _get_tumblr_test_data(filename: str) -> str:
    """Get the path to a file in tumblr/test_data."""
    # https://stackoverflow.com/a/18489147
    base_path = getsourcefile(lambda: 0)
    assert base_path is not None
    return os.path.join(
        os.path.dirname(os.path.abspath(base_path)),
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
            "/v2/blog/knuxify/posts",
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
            "/v2/blog/punkitt-is-here/posts",
            query_string={
                "id": "781681205274886144",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Test post 3: Answer to ask
    with open(_get_tumblr_test_data("post_ask.json")) as test_data:
        httpserver.expect_request(
            "/v2/blog/knuxify/posts",
            query_string={
                "id": "732094755733929984",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Test post 4: Self-reblog, tags only
    with open(_get_tumblr_test_data("post_self_reblog_tags_only.json")) as test_data:
        httpserver.expect_request(
            "/v2/blog/knuxify/posts",
            query_string={
                "id": "799921945450840064",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Special case post 1: Poll with missing answer
    with open(_get_tumblr_test_data("post_broken_poll_answer.json")) as test_data:
        httpserver.expect_request(
            "/v2/blog/janmisali/posts",
            query_string={
                "id": "728090722324119552",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Special case post 2: Blocks in rows out of order, plus truncate_after
    with open(
        _get_tumblr_test_data("post_blocks_out_of_order_and_truncation.json")
    ) as test_data:
        httpserver.expect_request(
            "/v2/blog/toastyyjams/posts",
            query_string={
                "id": "808575515119255552",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Special case post 3: Image with its attribute value set to an empty list
    with open(_get_tumblr_test_data("post_attrib_empty_list.json")) as test_data:
        httpserver.expect_request(
            "/v2/blog/mousegirlheart/posts",
            query_string={
                "id": "796276113056923648",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Special case post 4: Posts listed as "hidden due to its potentially sensitive nature"
    # return a literal 404 HTML page through the API, due to what I can only assume
    # is a Tumblr bug?
    with open(_get_tumblr_test_data("html_404.html")) as test_data:
        httpserver.expect_request(
            "/v2/blog/princessdollknight/posts",
            query_string={
                "id": "810480162328215552",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_data(test_data.read(), status=404)

    # Special case post 5: Old post where part of the reblog chain was converted
    # into blockquotes
    with open(_get_tumblr_test_data("post_reblog_chain_blockquotes.json")) as test_data:
        httpserver.expect_request(
            "/v2/blog/worldheritagepostorganization/posts",
            query_string={
                "id": "806582021235277824",
                "npf": "true",
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Result of post_id=0
    with open(_get_tumblr_test_data("post_id0.json")) as test_data:
        httpserver.expect_request(
            "/v2/blog/knuxify/posts",
            query_string={"id": "0", "npf": "true", "api_key": "consumer_key"},
        ).respond_with_json(json.load(test_data))

    # Poll results for Ultimate NPF Test Post
    with open(_get_tumblr_test_data("poll_results_npftest.json")) as test_data:
        httpserver.expect_request(
            "/v2/polls/knuxify/730903802869317632/e040d07a-ca6a-4751-8df5-ebaa1719222e/results",
            query_string={
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Test blog 1: knuxify
    # https://www.tumblr.com/knuxify
    with open(_get_tumblr_test_data("blog_knuxify.json")) as test_data:
        httpserver.expect_request(
            "/v2/blog/knuxify/info",
            query_string={
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # Poll results: invalid poll ID
    with open(_get_tumblr_test_data("poll_results_invalid_id.json")) as test_data:
        httpserver.expect_request(
            "/v2/polls/knuxify/730903802869317632/bogus/results",
            query_string={
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data), status=400)

    # Poll results for broken poll answer test
    with open(
        _get_tumblr_test_data("poll_results_broken_poll_answer.json")
    ) as test_data:
        httpserver.expect_request(
            "/v2/polls/janmisali/728090722324119552/d0b6b130-0f4b-46b1-af77-1ea386c85529/results",
            query_string={
                "api_key": "consumer_key",
            },
        ).respond_with_json(json.load(test_data))

    # 404 responses
    with open(_get_tumblr_test_data("resp_404.json")) as test_data:
        data = json.load(test_data)

        httpserver.expect_request(
            "/v2/blog/a/info",
        ).respond_with_json(data, status=404)

        httpserver.expect_request(
            "/v2/blog/a/posts",
        ).respond_with_json(data, status=404)

        httpserver.expect_request(
            "/v2/blog/knuxify/posts",
            query_string={"id": "1234", "npf": "true", "api_key": "consumer_key"},
        ).respond_with_json(data, status=404)

        httpserver.expect_request(
            "/v2/polls/knuxify/730903802869317632/f040d07a-ca6a-4751-8df5-ebaa1719222e/results",
            query_string={"api_key": "consumer_key"},
        ).respond_with_json(data, status=404)

        httpserver.expect_request(
            "/v2/polls/knuxify/1234/e040d07a-ca6a-4751-8df5-ebaa1719222e/results",
            query_string={"api_key": "consumer_key"},
        ).respond_with_json(data, status=404)

        httpserver.expect_request(
            "/v2/polls/a/1234/e040d07a-ca6a-4751-8df5-ebaa1719222e/results",
            query_string={"api_key": "consumer_key"},
        ).respond_with_json(data, status=404)

    # Private blog
    with open(_get_tumblr_test_data("blog_private.json")) as test_data:
        httpserver.expect_request(
            "/v2/blog/private-blog-test/info",
            query_string={"api_key": "consumer_key"},
        ).respond_with_json(json.load(test_data), status=404)

    # Private post
    with open(_get_tumblr_test_data("post_private.json")) as test_data:
        httpserver.expect_request(
            "/v2/blog/private-blog-test/posts",
            query_string={
                "id": "808188296199094272",
                "npf": "true",
                "api_key": "consumer_key",
            },
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

    if consumer_key and consumer_secret:
        t = TumblrAPI([(consumer_key, consumer_secret)])
    else:
        t = TumblrAPI([("consumer_key", "consumer_secret")])
        t.api_base = tumblr_api_server.url_for("/")

    return t
