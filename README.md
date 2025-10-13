# fxtumblr v2

*Like [TwitFix](https://github.com/robinuniverse/TwitFix), but for Tumblr.*

## WIP WIP WIP!!!

This is a complete ground-up rewrite of fxtumblr focused on cleaner code and maintainability. It is heavily work-in-progress and is not yet usable.

## Why?

The initial goal was to make Tumblr embeds nicer on Discord. At the time of fxtumblr's creation, Discord's Tumblr embeds were hardly usable - they only showed a small portion of the post, stripped any images beyond the first one and had no proper attribution data (the post would just show up attributed to the person whose blog was linked, even if it was a reblog). From there, it grew far above a simple embedding tool, gaining the ability to render Tumblr threads to PNG.

Since then, [Discord has improved its Tumblr embeds considerably](https://discord.com/blog/discord-patch-notes-august-4-2025). They now have their own special embed type and can display multiple images, proper attribution and retain some formatting. There are, however, still things that Discord's embedder *can't* do - fxtumblr aims to provide a much more faithful embedder alternative.

## Development

### Installing pre-commit hooks

We have a pre-commit config that runs ruff to check for formatting issues before making a commit. It is highly recommented that you install this hook.

To do this, install `pre-commit` and run `pre-commit install` in the repo's root.

### Running the test suite

The test suite uses `pytest`. Note that you will need test dependencies to run the tests; you can get them with `poetry install --with test`.

To run the tests, run `python3 -m pytest`.

By default, tests that interact with the Tumblr API use a mock server; however, you can provide a custom API consumer key/secret for testing with the real Tumblr API through the `FXTUMBLR_TEST_TUMBLR_KEY` and `FXTUMBLR_TEST_TUMBLR_SECRET` environment variables.
