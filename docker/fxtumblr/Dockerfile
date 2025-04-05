# fxtumblr dockerfile.
# NOTE: This file expects the build context to be set to the fxtumblr source code directory.

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim as base

# ...configurable args start here...

# The default listening port is 7878. If you need to use a different
# port, change the line below.
ENV FXTUMBLR_PORT=7878

# By default, hypercorn is configured to start 4 workers. If you want to
# change this, change the line below.
ENV FXTUMBLR_WORKERS=4

# ...configurable args end here...


# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/fxtumblr

# Copy the source code into the container
COPY . .

# Install fxtumblr dependencies.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install . .[statstool]

# Add fxtumblr user
ARG UID=10001
ARG GID=10001
RUN groupadd -g "${GID}" fxtumblr
RUN useradd -m -u ${UID} -g fxtumblr fxtumblr

# Expose the listening port
EXPOSE ${FXTUMBLR_PORT}

# Run the main fxtumblr server
CMD docker/fxtumblr/run-app-docker.sh "$FXTUMBLR_PORT" "$FXTUMBLR_WORKERS"
