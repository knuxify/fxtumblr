# SPDX-License-Identifier: MIT
"""Functions for doing renders and handling render tasks."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

import aiofiles
import aiofiles.os
import jinja2

from fxtumblr import config
from fxtumblr.render import RenderFiletype, RenderModifier
from fxtumblr.render.paths import get_render_path

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

    #: Dictionary containing the task parameters.
    data: dict

    @classmethod
    def from_dict(cls, data: dict):
        """Convert a render task dict into a RenderTask object."""
        if "id" not in data:
            raise ValueError("Invalid render task: no task ID")

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
    async def run(self, worker: "Worker") -> bool:
        """Run the task represented by this class."""


@dataclass
class RenderTaskPost(RenderTask):
    """Task for rendering a post."""

    task_type = RenderTaskType.POST

    blog_id: str
    post_id: int
    modifiers: list[RenderModifier]

    @classmethod
    def from_dict(cls, data: dict):
        """Convert a render task dict into a RenderTask object."""
        data_clean = {
            k: v for k, v in data.items() if k in ["blog_id", "post_id", "modifiers"]
        }
        try:
            return cls(task_id=data["id"], data=data_clean, **data_clean)
        except TypeError as e:
            raise ValueError("Invalid render task: invalid data") from e

    async def run(self, worker: "Worker") -> bool:
        """Run the post render task."""

        # Get post data
        post = await worker.tumblr.get_post(self.blog_id, self.post_id)
        if not post:
            return False

        # Filenames use the blog name; if we got a blog ID, make sure
        # we use the name instead
        blog_name = post.blog.name

        # Render the post to HTML
        html = render_template.render(post=post, modifiers=self.modifiers)

        # If render debugging is enabled, save the HTML to a file
        if config["render"].get("debug", False):

            async def _save_render(self, blog_name, html):
                path = get_render_path(
                    blog_name,
                    self.post_id,
                    modifiers=self.modifiers,
                    filetype=RenderFiletype.HTML,
                )
                async with aiofiles.open(path, "w") as html_file:
                    await html_file.write(html)

            await asyncio.create_task(_save_render(self, blog_name, html))

        # Generate the PNG
        render_path_png = get_render_path(
            blog_name,
            self.post_id,
            modifiers=self.modifiers,
            filetype=RenderFiletype.PNG,
        )

        await worker.browser.screenshot(
            "", ScreenshotFiletype.PNG, render_path_png, html_data=html
        )

        return True
