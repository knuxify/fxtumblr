#!/bin/sh
export QUART_APP=fxtumblr.app
hypercorn -w 4 'fxtumblr.app' -b 0.0.0.0:7878
