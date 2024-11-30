#!/bin/sh

[ ! "$FXTUMBLR_WORKERS" ] && export FXTUMBLR_WORKERS=$2
[ ! "$FXTUMBLR_PORT" ] && export FXTUMBLR_PORT=$1

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

[ -e "stats.db" ] && chown -R fxtumblr:fxtumblr stats.db
runuser -u fxtumblr -- hypercorn -w "${FXTUMBLR_WORKERS}" "fxtumblr.app" -b 0.0.0.0:"${FXTUMBLR_PORT}"
exit $?
