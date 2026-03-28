# SPDX-License-Identifier: MIT
"""Test configuration and fixtures for fxtumblr tests."""

import json
import os
from inspect import getsourcefile

import pytest
from pytest_httpserver.httpserver import HTTPServer

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
def tumblr_api_server(httpserver: HTTPServer):
    """Test fixture that simulates Tumblr's API."""

    # Helper functions

    def _define_api_route(
        data_filename: str,
        path: str,
        query_string: dict[str, str] | None = None,
        status_code: int = 200,
        is_json: bool = True,
    ):
        """Define API route in HTTP mock server."""
        nonlocal httpserver
        with open(_get_tumblr_test_data(data_filename)) as test_data:
            request = httpserver.expect_request(path, query_string=query_string)
            if is_json:
                request.respond_with_json(json.load(test_data), status=status_code)
            else:
                request.respond_with_data(test_data.read(), status=status_code)

    def _define_post(
        data_filename: str,
        blog_name: str,
        post_id: int,
        status_code: int = 200,
        is_json: bool = True,
    ):
        """Define a post request."""
        _define_api_route(
            data_filename,
            f"/v2/blog/{blog_name}/posts",
            query_string={
                "id": str(post_id),
                "npf": "true",
                "reblog_info": "true",
                "api_key": "consumer_key",
            },
            status_code=status_code,
            is_json=is_json,
        )

    def _define_blog(
        data_filename: str, blog_name: str, status_code: int = 200, is_json: bool = True
    ):
        """Define a blog request."""
        nonlocal httpserver

        _define_api_route(
            data_filename,
            f"/v2/blog/{blog_name}/info",
            query_string={
                "api_key": "consumer_key",
            },
            status_code=status_code,
            is_json=is_json,
        )

    def _define_poll_results(
        data_filename: str,
        blog_name: str,
        post_id: int,
        poll_id: str,
        status_code: int = 200,
        is_json: bool = True,
    ):
        """Define a poll results request."""
        nonlocal httpserver

        _define_api_route(
            data_filename,
            f"/v2/polls/{blog_name}/{post_id}/{poll_id}/results",
            query_string={
                "api_key": "consumer_key",
            },
            status_code=status_code,
            is_json=is_json,
        )

    # Test post 1: Ultimate NPF Test Post
    # https://www.tumblr.com/knuxify/730903802869317632/the-ultimate-test-post-v2
    _define_post("post_npftest.json", "knuxify", 730903802869317632)

    # Test post 2: Random reblog chain
    # https://www.tumblr.com/punkitt-is-here/781681205274886144
    _define_post("post_reblogs.json", "punkitt-is-here", 781681205274886144)

    # Test post 3: Answer to ask
    _define_post("post_ask.json", "knuxify", 732094755733929984)

    # Test post 4: Self-reblog, tags only
    _define_post("post_self_reblog_tags_only.json", "knuxify", 799921945450840064)

    # Test post 5: Text with formatting
    _define_post("post_text_formatting.json", "knuxify", 811047603701694464)

    # Test post 6: Text with subtype
    _define_post("post_text_subtype.json", "knuxify", 811047588066476032)

    # Test post 7: Video in post
    _define_post("post_video.json", "knuxify", 722920574030053376)

    # Test post 8: Ask and answer
    _define_post("post_ask_simple.json", "knuxify", 811081495873814528)

    # Special case post 1: Poll with missing answer
    _define_post("post_broken_poll_answer.json", "janmisali", 728090722324119552)

    # Special case post 2: Blocks in rows out of order, plus truncate_after
    _define_post(
        "post_blocks_out_of_order_and_truncation.json",
        "toastyyjams",
        808575515119255552,
    )

    # Special case post 3: Image with its attribute value set to an empty list
    _define_post("post_attrib_empty_list.json", "mousegirlheart", 796276113056923648)

    # Special case post 4: Posts listed as "hidden due to its potentially sensitive nature"
    # return a literal 404 HTML page through the API, due to what I can only assume
    # is a Tumblr bug?
    _define_post(
        "html_404.html",
        "princessdollknight",
        810480162328215552,
        status_code=404,
        is_json=False,
    )

    # Special case post 5: Old post where part of the reblog chain was converted
    # into blockquotes
    _define_post(
        "post_reblog_chain_blockquotes.json",
        "worldheritagepostorganization",
        806582021235277824,
    )

    # Result of post_id=0
    _define_post("post_id0.json", "knuxify", 0)

    # Test blog 1: knuxify
    # https://www.tumblr.com/knuxify
    _define_blog("blog_knuxify.json", "knuxify", status_code=404, is_json=False)

    # Poll results for Ultimate NPF Test Post
    _define_poll_results(
        "poll_results_npftest.json",
        "knuxify",
        730903802869317632,
        "e040d07a-ca6a-4751-8df5-ebaa1719222e",
    )

    # Poll results: invalid poll ID
    _define_poll_results(
        "poll_results_invalid_id.json",
        "knuxify",
        730903802869317632,
        "bogus",
        status_code=400,
    )

    # Poll results for broken poll answer test
    _define_poll_results(
        "poll_results_broken_poll_answer.json",
        "janmisali",
        728090722324119552,
        "d0b6b130-0f4b-46b1-af77-1ea386c85529",
    )

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
            query_string={
                "id": "1234",
                "npf": "true",
                "reblog_info": "true",
                "api_key": "consumer_key",
            },
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
    _define_blog("blog_private.json", "private-blog-test", status_code=404)

    # Private post
    _define_post(
        "post_private.json", "private-blog-test", 808188296199094272, status_code=404
    )

    return httpserver


@pytest.fixture
def tumblr_api(tumblr_api_server: HTTPServer):
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
