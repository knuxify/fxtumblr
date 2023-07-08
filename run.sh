#!/bin/sh
export QUART_ENV=development
export QUART_APP=fxtumblr
hypercorn -w 4 'fxtumblr:app'
