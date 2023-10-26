# fxtumblr

*Like [TwitFix](https://github.com/robinuniverse/TwitFix), but for Tumblr*

## Why?

Because Tumblr embeds suck, that's why. If you're a Tumblr user and you keep sending funny posts to your non-Tumblr friends on places like Discord, you probably know. If you're the non-Tumblr friend in question (like me) then you doubly so know.

I got so annoyed at the status quo that I made this to fix it. The initial version was quickly written in one day, and improvements are still being made.

This is heavily inspired by fxtwitter.com, vxtwitter.com, twxtter/`s/i/x` and so on, but it works with Tumblr instead.

## How to use it

Simply replace `www.tumblr.com` in your URL with the URL of the fxtumblr instance you want to use.

You can try out the test instance, `fx.dithernet.org`. Note that this instance is still a bit unstable, and may disappear at any moment; if you'd like to see a proper instance pop up at some point, [feel free to donate](https://paypal.me/knuxfanwin8).

## Setting up for self-hosting

* Install Python 3
* Get all the dependencies with `pip3 install -r requirements.txt`
* Copy `config.yml.sample` to `config.yml`
* Modify config according to your needs
* Install nginx and Hypercorn, copy nginx config (`fxtumblr.nginx`) into your sites-available, `ln -s` it into sites-enabled
* Run `./run.sh`

## Enabling thread rendering support

Unfortunately, standard embeds are too limited to fully display an entire Tumblr thread. Thus, there's optional support for rendering threads using a headless browser of your choosing (Chromium, Firefox or WebKit) using the `playwright` package.

In order to make use of it, set `renders_enable` in your config. Then, run `playwright install` to initialize Playwright. A copy of each of the browsers should be downloaded automatically on first launch.

You will also have to download Tumblr's web fonts for the best experience - see fonts/README.md. You should also get a system font that has emoji suport (like Noto Emoji).
