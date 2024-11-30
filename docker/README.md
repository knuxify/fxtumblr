# fxtumblr docker scripts

This folder contains the necessary Dockerfiles and an example docker-compose setup for running fxtumblr in Docker.

With this setup, fxtumblr and the renderer are run in separate containers. The fxtumblr container is based on Alpine Linux for smaller container size, and the renderer container runs Debian for better browser compatibility.

Note that this setup requires a reverse-proxy. I use nginx on the host for this, but something like Caddy should work as well.

# Using docker-compose

- Copy `docker-compose.yml.sample` into **the root of fxtumblr's source code**:
  ```
  $ cd /path/to/fxtumblr
  $ cp docker/docker-compose.yml.sample .
  ```
- Modify the file as explained in the comments.
- Copy the example config (`config.yml.docker`) into the root of fxtumblr's source code:
  ```
  $ cp docker/config.yml.docker config.yml
  ```
- Set the configuration options as needed.
- Run with regular docker compose options: `docker compose up` to start, `docker compose down` to stop.
