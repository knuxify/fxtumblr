# fxtumblr

*Like [TwitFix](https://github.com/robinuniverse/TwitFix), but for Tumblr*

## Why?

Because Tumblr embeds suck, that's why. If you're a Tumblr user and you keep sending funny posts to your non-Tumblr friends on places like Discord, you probably know. If you're the non-Tumblr friend in question (like me) then you doubly so know.

I got so annoyed at the status quo that I made this to fix it. The initial version was quickly written in one day, and improvements are still being made.

This is heavily inspired by fxtwitter.com, vxtwitter.com, twxtter/`s/i/x` and so on, but it works with Tumblr instead.

## How to use it

Simply replace `www.tumblr.com` in your URL with the URL of the fxtumblr instance you want to use.

You can also try out the official instance at `tpmblr.com` (or `fx.dissonant.dev`). For Discord users - you can post a tumblr.com link, then in the next message type `s/u/p`; this will automatically replace `tumblr.com` in the previous message with `tpmblr.com`.

## Setting up for self-hosting

* Install Python 3
* Create a venv for the packages: `python3 -m venv venv`, then `. venv/bin/activate`
* Get all the dependencies with `pip3 install -r requirements.txt`
* Copy `config.yml.sample` to `config.yml`
* Modify config according to your needs
* Install nginx and Hypercorn, copy nginx config (`fxtumblr.nginx`) into your sites-available, modify it to use your domainn name, `ln -s` it into sites-enabled
* Install Redis, set it up via `/etc/redis.conf`, apply the settings to the config file
* Run `./run.sh`

## Enabling thread rendering support

Unfortunately, standard embeds are too limited to fully display an entire Tumblr thread. Thus, there's optional support for rendering threads using a headless version of Chrome/Chromium using the `pyppeteer` package.

In order to make use of it, set `renders_enable` in your config. A copy of Chrome should be downloaded automatically on first launch.

You will also have to download Tumblr's web fonts for the best experience - see fonts/README.md. You should also get a system font that has emoji suport (like Noto Emoji).
