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

# Install Chromium and fxtumblr dependencies.
RUN apt update
RUN apt install -y gconf-service libasound2 libatk1.0-0 libatk-bridge2.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget libcairo-gobject2 libxinerama1 libgtk2.0-0 libpangoft2-1.0-0 libthai0 libpixman-1-0 libxcb-render0 libharfbuzz0b libdatrie1 libgraphite2-3 libgbm1
RUN apt install -y fonts-noto-color-emoji
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r requirements.txt
RUN playwright install --with-deps chromium

# Add fxtumblr user
ARG UID=10001
ARG GID=10001
RUN groupadd -g "${GID}" fxtumblr-render
RUN useradd -m -u ${UID} -g fxtumblr-render fxtumblr-render

# Copy the source code into the container
COPY . .

# Expose the listening port
EXPOSE ${FXTUMBLR_RENDER_PORT}

# Run the main fxtumblr server
CMD docker/fxtumblr-render/run-renderer-docker.sh
