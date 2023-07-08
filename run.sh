#!/bin/sh
export QUART_ENV=development
export QUART_APP=fxtumblr
gunicorn -w 4 'fxtumblr:app'
