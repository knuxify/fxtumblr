# fxtumblr v2

*Like [TwitFix](https://github.com/robinuniverse/TwitFix), but for Tumblr.*

## Why?

The initial goal was to make Tumblr embeds nicer on Discord. At the time of fxtumblr's creation, Discord's Tumblr embeds were hardly usable - they only showed a small portion of the post, stripped any images beyond the first one and had no proper attribution data (the post would just show up attributed to the person whose blog was linked, even if it was a reblog). From there, it grew far above a simple embedding tool, gaining the ability to render Tumblr threads to PNG.

Since then, [Discord has improved its Tumblr embeds considerably](https://discord.com/blog/discord-patch-notes-august-4-2025). They now have their own special embed type and can display multiple images, proper attribution and retain some formatting. There are, however, still things that Discord's embedder *can't* do - fxtumblr aims to provide a much more faithful embedder alternative.

## Setup for self-hosting

### With Docker

See `docker/README.md`. An example docker-compose.yml file is provided there for your convenience.

### Manually

fxtumblr consists of two processes: the main embed/web app process (`fxtumblr` module) and the renderer (`fxtumblr_render` module). Both processes need to be launched separately.

Install prerequisites: `python3`, `python3-pip`, `python3-setuptools`, `python3-setuptools-scm` and `redis`. Make sure that Redis is running.

Install the dependencies for both (this will also install fxtumblr as a module, which is an unfortunate limitation of pip - we can't *just* install the dependencies):

```bash
pip3 install .[embed-server,render-playwright]
```

Run the main server process with `./run_server.sh`, and the renderer process with `./run_renderer.sh`.

## Statistics

fxtumblr can be configured to collect basic usage statistics by setting `stats.enabled` to `true` in the config. The following data is collected:

* Amount of post hits
* Amount of unique post hits (a post remains unique for 24 hours after its first embed)
* Amount of errors encountered during Tumblr API query, embedding and renders

Notably, **no user data is collected**. The statistics are fully anonymous; post blog/IDs are hashed.

*Note that an instance admin can still choose to trace requests in other ways, e.g. by configuring access logging in their reverse proxy or by looking at render filenames if caching to the disk is enabled.*

These statistics are exposed over a Prometheus-compatible API endpoint, `/_stats`. This endpoint can be password-protected.

## Development

### Installing pre-commit hooks

We have a pre-commit config that runs ruff to check for formatting issues before making a commit and mypy to do type checks. It is highly recommented that you install this hook.

To do this, install `pre-commit` and run `pre-commit install` in the repo's root.

### Running the test suite

The test suite uses `pytest`. Note that you will need test dependencies to run the tests; you can get them with `poetry install --with test`.

To run the tests, run `poetry run python3 -m pytest`.

By default, tests that interact with the Tumblr API use a mock server; however, you can provide a custom API consumer key/secret for testing with the real Tumblr API through the `FXTUMBLR_TEST_TUMBLR_KEY` and `FXTUMBLR_TEST_TUMBLR_SECRET` environment variables. (pytest-env is in test dependencies, so you can also create a file called `.env` in the repository root and place the variables there.)
