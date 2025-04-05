# fxtumblr

*Like [TwitFix](https://github.com/robinuniverse/TwitFix), but for Tumblr*

## Why?

Because Tumblr embeds suck, that's why. If you're a Tumblr user and you keep sending funny posts to your non-Tumblr friends on places like Discord, you probably know. If you're the non-Tumblr friend in question (like me) then you doubly so know. I got so annoyed at the status quo that I made this to fix it.

This is heavily inspired by fxtwitter.com, vxtwitter.com, twxtter/`s/i/x` and so on, but it works with Tumblr instead.

## How to use it

Simply replace `www.tumblr.com` in your URL with the URL of the fxtumblr instance you want to use.

You can also try out the official instance at `tpmblr.com` (or `fx.dissonant.dev`). For Discord users - you can post a tumblr.com link, then in the next message type `s/u/p`; this will automatically replace `tumblr.com` in the previous message with `tpmblr.com`.

## Privacy

The only information used by fxtumblr is the post URL that is passed to it; no other data is collected by the software itself. By default, this data is not logged anywhere, but there are two optional mechanisms available to set in the `config.yml` file by the instance admin:

- `logging` prints a message with the post URL and modifiers every time a post is requested. This is mostly meant for debugging purposes, and should generally not be used in production (except for figuring out issues with the server). **Note that in the event of a failure, the post that caused the failure is always printed, even if this option is disabled.**
- `statistics` enabled anonymous statistics, which are saved in the cache and can be read by the instance admin using the `statstool.py` script.

For anonymous statistics, the following information is logged:

- The time of the request, rounded down to every 10 minutes (so e.g. 16:24 becomes 16:20);
- The modifiers passed to the post ("unroll", "dark");
- Hash (sha256) of the OP's blog name and post ID. This hash **cannot** be reversed back into the original URL.

Full disclosure - **the official instance at tpmblr.com has anonymous statistics enabled**. These are used only to keep traffic under control and act accordingly in the event of sudden failure or an increase in requests.

Admins may still be able to track requests, e.g. through nginx access logs (disabled on tpmblr.com) or by checking the renders folder.

## Setting up for self-hosting

* Install Python 3
* Create a venv for the packages:
  * Run `python3 -m venv venv`, then `. venv/bin/activate`; then get all the dependencies with `pip3 install -r requirements.txt`
  * For testing, the preferred way to do this is to use Hatch - install Hatch, run `hatch env create` and run the later shell scripts through `hatch run ./run-xxx.sh`
* Copy `config.yml.sample` to `config.yml`
* Modify config according to your needs
* Install nginx and Hypercorn, copy nginx config (`fxtumblr.nginx`) into your sites-available, modify it to use your domainn name, `ln -s` it into sites-enabled
* Install Redis, set it up via `/etc/redis.conf`, apply the settings to the config file
* Run `./run.sh` (and simultaneously `./run-renderer.sh` if you want rendering support - see next section).

### Running in Docker

It is also possible to run fxtumblr in a Docker container; see docker/README.md for more information.

### Enabling thread rendering support

Unfortunately, standard embeds are too limited to fully display an entire Tumblr thread. Thus, there's optional support for rendering threads using a headless web browser. (Renders are enabled on the official instance.)

In order to make use of it, set `renders_enable` in your config. Then, run `./run-renderer.sh` to start the renderer process.

The available backends (selectable with `renders_browser` in the config) are:

- `pyppeteer` (default) - uses pyppeteer package and system install of Chromium.
- `playwright-chromium` - uses Playwright and Chromium.
- `playwright-firefox` - uses Playwright and Firefox.
- `playwright-webkit` - uses Playwright and WebKit.

Pyppeteer is the simplest. Playwright is the most accurate, up-to-date and supports more platforms (and will likely become the default in the near future). Which one works best is up to you.

Run `playwright install chromium` to let Playwright download its own Chromium build.

If you want to use a custom Chromium build instead of the one provided by Playwright, set the `renders_chromium_path` config option to the path of the Chromium executable.

You will also have to download Tumblr's web fonts for the best experience - see fonts/README.md. You should also get a 
system font that has emoji suport (like Noto Emoji).

By default, renders are only generated if any of the following is true:

- The post is too long to fit in a standard embed
- The post contains any kind of formatting (bold/italic/custom font/etc.)
- The post contains more than 1 image/more than 1 video
- The post contains a poll or other exotic block type

If you'd like to generate renders for all posts unconditionally on the server, set `renders_always_render` to `true`. Otherwise, users can force a render on a post by appending `?forcerender` to the embed URL.
