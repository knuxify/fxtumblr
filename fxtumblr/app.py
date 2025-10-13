# SPDX-License-Identifier: MIT
"""Quart app entrypoint, setup and routes."""

import logging

from quart import Quart, render_template, send_from_directory

from . import config

app = Quart(__name__)
logger = logging.getLogger(__name__)

app.jinja_env.globals["domain"] = config["instance"]["domain"]
app.jinja_env.globals["instance"] = {
    "name": config["instance"]["name"],
    "contact_email": config["instance"]["contact_email"],
}


@app.route("/robots.txt")
async def robots_txt():
    """Provide the robots.txt file."""
    return await send_from_directory(app.static_folder, "robots.txt")


@app.route("/")
async def index():
    """Render the index page."""
    return await render_template("index.html")
