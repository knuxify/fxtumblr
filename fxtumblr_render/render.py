# SPDX-License-Identifier: MIT
"""Functions for doing renders and handling render tasks."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar

import aiofiles
import jinja2

from fxtumblr.cache import cache
from fxtumblr.render import RenderFiletype, RenderModifier
from fxtumblr.render.paths import (
    get_render_cache_key,
    get_render_path,
)

from . import config
from .screenshot import ScreenshotFiletype

if TYPE_CHECKING:
    from .server import Worker  # circular import


# Render template setup
template_loader = jinja2.PackageLoader("fxtumblr_render")
template_env = jinja2.Environment(loader=template_loader, autoescape=True)
render_template = template_env.get_template("render.html")


class RenderTaskType(StrEnum):
    """Types of render tasks."""

    POST = "post"


@dataclass
class RenderTask(ABC):
    """Single task for the renderer."""

    #: Unique ID of the task.
    task_id: str

    #: Type of the task, from the RenderTaskType enum.
    task_type: ClassVar[RenderTaskType]

    @classmethod
    def from_dict(cls, data: dict):
        """Convert a render task dict into a RenderTask object."""
        if "task_type" not in data:
            raise ValueError("Invalid render task: no task type")

        elif data["task_type"] == RenderTaskType.POST:
            out = RenderTaskPost.from_dict(data)

            return out

        else:
            raise ValueError(
                f"Invalid render task: unknown render type {data['task_type']}"
            )

    @abstractmethod
    async def run(self, worker: "Worker") -> Any:
        """Run the task represented by this class."""


@dataclass
class RenderTaskPost(RenderTask):
    """Task for rendering a post."""

    task_type = RenderTaskType.POST

    blog_name: str
    post_id: int
    modifiers: list[RenderModifier]
    filetype: RenderFiletype

    @classmethod
    def from_dict(cls, data: dict):
        """Convert a render task dict into a RenderTask object."""
        try:
            blog_name = data["blog_name"]
            post_id = int(data["post_id"])
            modifiers = [RenderModifier(mod) for mod in data.get("modifiers", [])]
            filetype = RenderFiletype(data["filetype"])

            # For the task ID, we re-use the render path generation function; this ensures that
            # two tasks representing the same post/parameters
            # have the same ID and can be deduplicated.
            task_id = get_render_path(blog_name, post_id, modifiers, filetype)

            return cls(
                task_id=task_id,
                blog_name=blog_name,
                post_id=post_id,
                modifiers=modifiers,
                filetype=filetype,
            )

        except (TypeError, KeyError, ValueError) as e:
            print(e)
            raise ValueError("Invalid render task: invalid data") from e

    async def _save_render(self, data: str | bytes, filetype: RenderFiletype):
        """
        Save render data to a file. Helper function for run().

        :param data: Data to write, string or bytes.
        :param filetype: Filetype to use.
        """
        path = get_render_path(
            self.blog_name,
            self.post_id,
            modifiers=self.modifiers,
            filetype=filetype,
        )

        if isinstance(data, bytes):
            async with aiofiles.open(path, "wb") as html_file:
                await html_file.write(data)
        else:
            async with aiofiles.open(path, "w") as html_file:
                await html_file.write(data)

    async def run(self, worker: "Worker") -> bytes | None:
        """Run the post render task."""

        # Get post data
        post = await worker.tumblr.get_post(self.blog_name, self.post_id)
        if not post:
            return None

        # Render the post to HTML
        html = render_template.render(post=post, modifiers=self.modifiers)

        # If render debugging is enabled, save the HTML to a file
        if config.render.debug:
            await asyncio.create_task(self._save_render(html, RenderFiletype.HTML))

        # Generate the PNG
        render_path_png = get_render_path(
            self.blog_name,
            self.post_id,
            modifiers=self.modifiers,
            filetype=RenderFiletype.PNG,
        )

        screenshot_data = await worker.browser.screenshot(
            "", ScreenshotFiletype.PNG, render_path_png, html_data=html
        )

        if config.render.mem_cache_timeout:
            cache_key = get_render_cache_key(
                self.blog_name, self.post_id, self.modifiers, RenderFiletype.PNG
            )

            await cache.set_bin(
                cache_key, screenshot_data, timeout=config.render.mem_cache_timeout
            )

        if config.render.disk_cache_timeout:
            await asyncio.create_task(self._save_render(screenshot_data, self.filetype))

        return screenshot_data
