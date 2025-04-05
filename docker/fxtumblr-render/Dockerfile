# fxtumblr dockerfile.
# NOTE: This file expects the build context to be set to the fxtumblr source code directory.

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim as base

# ...configurable args start here...

# The default renderer port is 6500. If you need to use a different
# port, change the line below.
ARG FXTUMBLR_RENDER_PORT=6500

# ...configurable args end here...


# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/fxtumblr

# Copy the source code into the container
COPY . .

# Install Chromium and fxtumblr dependencies.
RUN apt update
RUN apt install -y fonts-noto-color-emoji
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install . .[render-playwright]
RUN playwright install-deps chromium

# Add fxtumblr user
ARG UID=10001
ARG GID=10001
RUN groupadd -g "${GID}" fxtumblr-render
RUN useradd -m -u ${UID} -g fxtumblr-render fxtumblr-render

# Let Playwright install Chromium
USER fxtumblr-render
RUN playwright install chromium
USER root

# Expose the listening port
EXPOSE ${FXTUMBLR_RENDER_PORT}

# Run the main fxtumblr server
CMD docker/fxtumblr-render/run-renderer-docker.sh
