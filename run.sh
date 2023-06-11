#!/bin/sh
export FLASK_ENV=development
export FLASK_APP=fxtumblr
gunicorn -w 4 'fxtumblr:app'
