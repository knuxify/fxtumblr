#!/bin/sh
export FLASK_ENV=development
export FLASK_DEBUG=1
export FLASK_APP=fxtumblr
python3 -m flask run
