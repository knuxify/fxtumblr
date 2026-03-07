# SPDX-License-Identifier: MIT
"""Configuration access interface."""

import os
import tomllib
from dataclasses import dataclass
from typing import Literal, Self, Type

from pydantic import BaseModel, ValidationError


class ConfigInstance(BaseModel):
    """Instance configuration."""

    #: Name of the instance.
    name: str

    #: Base domain of the instance.
    domain: str

    #: Contact email listed on the index page.
    contact_email: str

    #: List of strings to show next to the instance name.
    motd: list[str] | None = None


class ConfigTumblr(BaseModel):
    """Tumblr API access configuration."""

    #: API keys. List of tuples containing consumer key and consumer secret.
    api_keys: list[tuple[str, str]]


class ConfigRedis(BaseModel):
    """Redis cache access configuration."""

    #: Redis host.
    host: str

    #: Redis port.
    port: int

    #: Redis password; None or empty string for no password.
    password: str | None = None

    #: Timeout after which post cache data is cleared, in seconds.
    #: Defaults to 10 minutes (60 * 10 = 600).
    timeout: int = 600


class ConfigStats(BaseModel):
    """Statistics configuration."""

    #: Whether or not to enable statistics.
    enabled: bool

    #: Optional password for the stats endpoint.
    password: str | None = None

    #: Timeout after which statistics data is cleared, in seconds.
    #: Defaults to 30 days (60 * 60 * 24 * 30 = 2592000).
    timeout: int = 2592000

    #: List of tuples with (blog name, post ID) to not count in statistics.
    ignore_posts: list[tuple[str, int]] | None = None


class ConfigRender(BaseModel):
    """Renderer configuration."""

    #: Render process host.
    host: str

    #: Render process port.
    port: int

    #: Path to the directory where renders will be cached.
    path: str | os.PathLike

    #: Render backend.
    backend: Literal["playwright-chromium"]

    #: Path to the browser executable; if None, uses the default for the backend.
    browser_executable: str | os.PathLike | None = None

    #: Amount of render workers (decides how many renders that can happen simultaneously).
    worker_count: int = 3

    #: If True, enables redirects from legacy render URLs to new URLs.
    #: (example.com/renders/blogname-postid.png)
    #: This is a compatiblity feature for instances that used to run v1,
    #: which is used to; new instances do not need to enable this.
    redirect_legacy_urls: bool = False

    #: Enable miscelaneous debug features.
    debug: bool = False

    #: Time after which renders cached in memory will be removed from the cache,
    #: in seconds.
    #: Set to 0 to disable memory caching.
    mem_cache_timeout: int = 60

    #: Time after whhich renders cached on the disk will be removed from the cache,
    #: in seconds.
    #: Set to 0 to disable disk caching (not recommended).
    disk_cache_timeout: int = 600


CONFIG_SECTIONS: dict[str, Type[BaseModel]] = {
    "instance": ConfigInstance,
    "tumblr": ConfigTumblr,
    "redis": ConfigRedis,
    "stats": ConfigStats,
    "render": ConfigRender,
}


@dataclass
class Config:
    """Base class for config access."""

    instance: ConfigInstance
    tumblr: ConfigTumblr
    redis: ConfigRedis
    stats: ConfigStats
    render: ConfigRender

    @classmethod
    def from_file(cls, path: str | os.PathLike) -> Self:
        """
        Take a path to a .toml file with configuration and read its contents
        into a Config object.

        :param path: Path to the configuration .toml file.
        :returns: The resulting Config object.
        :raises ValueError: if any of the values is invalid.
        """

        with open(path, "rb") as config_file:
            data = tomllib.load(config_file)

        return cls.from_data(data)

    @classmethod
    def from_data(cls, data: dict) -> Self:
        """
        Take the config data loaded as a dictionary and read its contents
        into a Config object.

        :param data: The data to parse.
        :returns: The resulting Config object.
        :raises ValueError: if any of the values is invalid.
        """

        configs = {}
        for section, config_class in CONFIG_SECTIONS.items():
            if section not in data:
                raise ValueError(f"Missing config section: {section}")

            try:
                configs[section] = config_class(**data[section])
            except ValidationError as e:
                raise ValueError(f"{section}: Invalid value ({e})") from e

        return cls(**configs)  # type: ignore[arg-type]
