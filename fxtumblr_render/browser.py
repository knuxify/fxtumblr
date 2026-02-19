# SPDX-License-Identifier: MIT
"""Common interfaces for various browser backends."""

import asyncio
from abc import ABC, abstractmethod
from os import PathLike
from typing import ClassVar, Type

from fxtumblr import config

from .screenshot import ScreenshotFiletype

# Imports for specific libraries
has_playwright: bool
try:
    import playwright.async_api
except ImportError:
    has_playwright = False
else:
    has_playwright = True


# Browser support


class Browser(ABC):
    """Base class for browser implementations."""

    @abstractmethod
    async def start(self):
        """Start the browser process."""

    @abstractmethod
    async def close(self):
        """Close the browser process."""

    @abstractmethod
    async def screenshot(
        self,
        url: str,
        filetype: ScreenshotFiletype,
        target_path: str | PathLike,
        width: int = 540,
        height: int = 100,
        full_page: bool = True,
        html_data: str | None = None,
    ):
        """
        Take a screenshot of the page.

        :param url: URL of the page to screenshot.
        :param filetype: File type of the resulting screenshot.
        :param target_path: Path to save the screenshot under.
        :param width: Viewport width.
        :param height: Viewport height.
        :param full_page: If True, takes a screenshot of the full page.
        :param html_data: If set, uses the given HTML data instead of the URL.
        """


# Playwright


class BrowserPlaywright(Browser):
    """Common implementation for playwright-based browsers."""

    #: Browser type, to be filled by subclasses.
    browser_type: ClassVar[str]

    async def start(self):
        """Start the browser process."""

        self.playwright_async = await playwright.async_api.async_playwright().start()
        browser_base = getattr(self.playwright_async, self.browser_type)

        executable_path = config["render"].get("browser_executable")
        if executable_path:
            self.browser = await browser_base.launch(executable_path=executable_path)
        else:
            self.browser = await browser_base.launch()

    async def close(self):
        """Close the browser process."""
        await self.browser.close()

    async def screenshot(
        self,
        url: str,
        filetype: ScreenshotFiletype,
        target_path: str | PathLike,
        width: int = 540,
        height: int = 100,
        full_page: bool = True,
        html_data: str | None = None,
    ):
        """
        Take a screenshot of the page.

        :param url: URL of the page to screenshot.
        :param filetype: File type of the resulting screenshot.
        :param target_path: Path to save the screenshot under.
        :param width: Viewport width.
        :param height: Viewport height.
        :param full_page: If True, takes a screenshot of the full page.
        :param html_data: If set, uses the given HTML data instead of the URL.
        """
        page = await self.browser.new_page()

        try:
            async with asyncio.timeout(10):
                await page.set_viewport_size({"width": width, "height": height})

                if html_data:
                    await page.set_content(html_data)
                else:
                    await page.goto(url)

                await page.screenshot(
                    path=str(target_path),
                    full_page=full_page,
                    omit_background=True,
                )
        except Exception as e:
            await page.close()
            raise e

        await page.close()


class BrowserPlaywrightChromium(BrowserPlaywright):
    """Browser implementation using Playwright's chromium support."""

    browser_type = "chromium"


# Backend list


#: List of available browser backends.
AVAILABLE_BACKENDS: dict[str, Type[Browser]] = {}

if has_playwright:
    AVAILABLE_BACKENDS["playwright-chromium"] = BrowserPlaywrightChromium


def get_browser() -> Browser:
    """
    Return a Browser object for the configured browser.

    :returns: Browser object representing the browser.
    :raises ValueError: if the browser backend in the config is invalid.
    """

    backend = config["render"]["backend"]

    if backend not in AVAILABLE_BACKENDS:
        raise ValueError(
            f"Unknown backend {backend}; available backends are {AVAILABLE_BACKENDS.keys()}. (Are you missing dependencies? See README for backend dependencies.)"
        )

    return AVAILABLE_BACKENDS[backend]()
