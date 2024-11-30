#!/bin/sh

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

if [ ! -e /opt/fxtumblr/renders ]; then
	mkdir /opt/fxtumblr/renders
fi
chown -R fxtumblr-render:fxtumblr-render /opt/fxtumblr/renders
runuser -u fxtumblr-render -- python3 -m fxtumblr_render
exit $?
