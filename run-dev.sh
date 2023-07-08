#!/bin/sh
export QUART_ENV=development
export QUART_DEBUG=1
export QUART_APP=fxtumblr
python3 -m quart run
