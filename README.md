# fxtumblr

*Like [TwitFix](https://github.com/robinuniverse/TwitFix), but for Tumblr*

## Why?

Because Tumblr embeds suck, that's why. If you're a Tumblr user and you keep sending funny posts to your non-Tumblr friends on places like Discord, you probably know. If you're the non-Tumblr friend in question (like me) then you doubly so know.

I got so annoyed at the status quo that I made this to fix it. The initial version was quickly written in one day, and improvements are still being made.

This is heavily inspired by fxtwitter.com, vxtwitter.com, twxtter/`s/i/x` and so on, but it works with Tumblr instead.

## How to use it

**TODO**: launch a flagship instance.

Simply replace `www.tumblr.com` in your URL with the URL of the fxtumblr instance you want to use.

## Setting up for self-hosting

* Install Python 3
* Get all the dependencies with `pip3 install -r requirements.txt`
* Copy `config.yml.sample` to `config.yml`
* Modify config according to your needs
* Install nginx and Hypercorn, copy nginx config (`fxtumblr.nginx`) into your sites-available, `ln -s` it into sites-enabled
* Run `./run.sh`

## Enabling thread rendering support

Unfortunately, standard embeds are too limited to fully display an entire Tumblr thread. Thus, there's optional support for rendering threads using a headless version of Chrome/Chromium using the `pyppeteer` package.

In order to make use of it, set `renders_enable` in your config. A copy of Chrome should be downloaded automatically on first launch.

You will also have to download Tumblr's web fonts for the best experience - see fonts/README.md.

## TODO

This is still a very early proof-of-concept, but it's good enough to kinda sorta work. Still, there are many quality-of-life improvements to be made:

- Add code to stich together multiple images, and use it to display attached images
- Add an alternative "post rendering" mode for very long threads or just as an alternative option
  - While we're at it - figure out what the description length limit is on Discord
- Apply some tweaks to the content on non-Discord platforms (not sure if we can get away with using Markdown in the description anywhere else...)
- Start a flagship instance (I hope nobody steals the domain from me...)
