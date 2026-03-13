#!/usr/bin/python3
"""Helper script for fetching test cases."""

import argparse
import asyncio
import json
import os
import traceback
from pathlib import Path

import aiofiles

from fxtumblr import config
from fxtumblr.tumblr import TumblrAPI

TEST_DATA_PATH = Path(os.path.dirname(os.path.realpath(__file__))) / "test_data"

tumblr = TumblrAPI(config.tumblr.api_keys)

# Argument parsing
parser = argparse.ArgumentParser(
    prog="update_test_data.py", description="Helper script for fetching test cases"
)
subparsers = parser.add_subparsers(dest="subcommand", help="subcommands")


parser_update = subparsers.add_parser("update-all", help="update all test cases")


parser_update_one = subparsers.add_parser("update-one", help="update one test case")
parser_update_one.add_argument(
    "filename", help="filename of the test to update (base name - e.g. poll_ask.json)"
)


parser_new = subparsers.add_parser("new", help="add a new test case")
subparsers_new = parser_new.add_subparsers(dest="type", help="type of object to pull")
parser_new.add_argument(
    "filename", help="filename to save the post under (base name only)"
)

parser_new_blog = subparsers_new.add_parser("blog")
parser_new_blog.add_argument("blog_id", help="Blog ID")

parser_new_post = subparsers_new.add_parser("post")
parser_new_post.add_argument("blog_id", help="Blog ID")
parser_new_post.add_argument("post_id", help="Post ID")

parser_new_poll_results = subparsers_new.add_parser("poll_results")
parser_new_poll_results.add_argument("blog_id", help="Blog ID")
parser_new_poll_results.add_argument("post_id", help="Post ID")
parser_new_poll_results.add_argument("poll_id", help="Poll ID")


async def update_one(filename: Path | str):
    """Update a file."""
    full_path = TEST_DATA_PATH / (os.path.basename(filename))

    async with aiofiles.open(full_path) as data:
        data_json = json.loads(await data.read())

    if "_fxt_meta_fetch" not in data_json:
        print(f"{os.path.basename(filename)}: no update URL")
        return False

    url, params = data_json["_fxt_meta_fetch"]

    api_response = await tumblr._get(url, params)

    if api_response.status != 200:
        print(
            f"{os.path.basename(filename)}: API response status {api_response.status}"
        )

    async with aiofiles.open(full_path, "w") as data:
        data_json = json.dumps(api_response.raw)
        await data.write(data_json)

    print(f"{os.path.basename(filename)}: updated")
    return True


async def update_all():
    """Update all test case files."""
    sem = asyncio.Semaphore(3)

    async def _update_one_wrap(filename: Path | str):
        async with sem:
            try:
                await update_one(filename)
            except:  # noqa: E722
                print(f"{os.path.basename(filename)}: error while updating")
                traceback.print_exc()

    async with asyncio.TaskGroup() as tg:
        _tasks = set()
        for path in TEST_DATA_PATH.glob("*.json"):
            _tasks.add(tg.create_task(_update_one_wrap(path)))


async def new(obj_type: str, obj_ids: list[str], filename: str):
    """Add a new test case."""
    full_path = TEST_DATA_PATH / (os.path.basename(filename))

    params = None
    if obj_type == "blog":
        url = f"/v2/blog/{obj_ids[0]}/info"
    elif obj_type == "post":
        url = f"/v2/blog/{obj_ids[0]}/posts"
        params = {"id": obj_ids[1], "npf": "true"}
    elif obj_type == "poll_results":
        url = f"/v2/polls/{obj_ids[0]}/{obj_ids[1]}/{obj_ids[2]}/results"
    else:
        raise ValueError("Unknown object type")

    api_response = await tumblr._get(url, params)

    if api_response.status != 200:
        print(
            f"{os.path.basename(filename)}: API response status {api_response.status}"
        )

    data_dict = api_response.raw.copy()
    data_dict["_fxt_meta_fetch"] = (url, params)
    data_json = json.dumps(data_dict)

    async with aiofiles.open(full_path, "w") as data:
        await data.write(data_json)


async def main():
    """Run script functions."""
    args = parser.parse_args()
    if args.subcommand == "update-all":
        await update_all()
    elif args.subcommand == "update-one":
        await update_one(args.filename)
    elif args.subcommand == "new":
        if args.type == "blog":
            await new(args.type, [args.blog_id], args.filename)
        elif args.type == "post":
            await new(args.type, [args.blog_id, args.post_id], args.filename)
        elif args.type == "poll_results":
            await new(
                args.type, [args.blog_id, args.post_id, args.poll_id], args.filename
            )
    else:
        print("No mode specified, see --help")


if __name__ == "__main__":
    asyncio.run(main())
