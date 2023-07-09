#!/bin/sh
export QUART_APP=fxtumblr
hypercorn -w 4 'fxtumblr:app'
