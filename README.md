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
* Install nginx and Gunicorn, copy nginx config (`fxtumblr.nginx`) into your sites-available, `ln -s` it into sites-enabled
* Run `./run.sh`
