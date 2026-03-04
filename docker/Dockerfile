# fxtumblr dockerfile.
# NOTE: This file expects the build context to be set to the fxtumblr source code directory.

ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim AS base

# ...configurable args start here...

# The default listening port is 7878. If you need to use a different
# port, change the line below.
ENV FXTUMBLR_PORT=7878

# The default renderer port is 6500. If you need to use a different
# port, change the line below.
ARG FXTUMBLR_RENDER_PORT=6500

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
COPY fxtumblr fxtumblr
COPY fxtumblr_render fxtumblr_render
COPY pyproject.toml pyproject.toml

# Install shared dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install .

# Add fxtumblr user
ARG UID=10001
ARG GID=10001
RUN groupadd -g "${GID}" fxtumblr && \
    useradd -m -u ${UID} -g fxtumblr fxtumblr

#
# Embed server
#
FROM base AS fxtumblr

# Install embed server dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install .[embed-server]

# Expose the listening port
EXPOSE ${FXTUMBLR_PORT}

# Run the main fxtumblr server
USER fxtumblr
ENTRYPOINT hypercorn -w "${FXTUMBLR_WORKERS}" fxtumblr.app -b "0.0.0.0:${FXTUMBLR_PORT}"

#
# Renderer
#
FROM base AS fxtumblr-render

# Install render server dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    apt update && \
    apt install -y fonts-noto-color-emoji && \
    python -m pip install .[render-playwright] && \
    playwright install-deps chromium

# Create renders directory
RUN mkdir -p renders && \
    chown -R 10001:10001 renders

USER fxtumblr
RUN playwright install chromium

# Expose the listening port
EXPOSE ${FXTUMBLR_RENDER_PORT}

# Run the render server
USER fxtumblr
ENTRYPOINT ["python3", "-m", "fxtumblr_render"]
