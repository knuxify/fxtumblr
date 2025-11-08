# SPDX-License-Identifier: MIT
"""Parser for Tumblr's NPF ("Neue Post Format") format."""

import datetime
import html
import itertools
import urllib.parse
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum, StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar, Self, Union

import dateutil
import emoji
import nh3
from frozendict import frozendict

if TYPE_CHECKING:
    # Placed in TYPE_CHECKING due to circular import
    from .api import TumblrAPI
    from .types import Blog, PollResults

##
# Helper classes/functions
##


class NPFParseError(Exception):
    """Exception raised when an error is encountered during NPF parsing."""


def safe_url(url: str) -> str:
    """Make an URL safe for putting in a HTML tag."""
    return urllib.parse.quote(url, safe="/:?&=")


def sanitize_html(html: str) -> str:
    """
    Sanitizes HTML to only include elements we add; second line of defense
    against arbitrary code execution.

    Update this whenever you add a new object.
    """
    return nh3.clean(
        html,
        tags={
            "p",
            "b",
            "i",
            "a",
            "small",
            "strong",
            "strike",
            "h1",
            "h2",
            "ul",
            "ol",
            "li",
            "blockquote",
            "span",
            "div",
            "figure",
            "img",
            "audio",
            "video",
            "source",
            "svg",
            "path",
            "aside",
            "use",
        },
        attributes={
            "*": {"class", "id"},
            "a": {"class", "id", "href"},
            "div": {"class", "id", "style"},
            "span": {"class", "id", "style"},
            "figure": {"class", "id", "data-orig-height", "data-orig-width"},
            "img": {"class", "id", "src", "data-orig-height", "data-orig-width"},
            "video": {
                "class",
                "id",
                "poster",
                "src",
                "controls",
                "data-orig-height",
                "data-orig-width",
            },
            "source": {"src", "type"},
            "audio": {"class", "id", "poster", "src", "controls", "muted"},
            "svg": {"class", "id", "xmlns", "height", "width", "role", "style"},
            "use": {"class", "id", "href"},
        },
    )


class WrapperType(Enum):
    """Enum for wrapper types."""

    HTML = 0
    Markdown = 1


@dataclass
class HTMLWrapper:
    """Helper class for storing HTML wrapper data."""

    #: First-level opening tag.
    open: str

    #: First-level closing tag.
    close: str

    # The next two variables are named after the indent_level
    # value in text blocks, which starts at 0 and increases
    # with each indent. Thus, going up an indent level means
    # going deeper, and going down an indent level means going
    # shallower.
    # Both are left empty for wrappers that do not need to
    # consider indentation levels.

    #: Tag for going up an indent level (deeper).
    up: str = ""

    #: Tag for going down an indent level (shallower).
    down: str = ""


@dataclass
class MarkdownWrapper:
    """Helper class for storing markdown wrapper data."""

    #: Opening tag.
    open: str

    #: Closing tag.
    close: str


##
# Media objects
# https://www.tumblr.com/docs/npf#media-objects
##


@dataclass
class Media:
    """Information about a single piece of media."""

    #: Mimetype of the media.
    type: str
    #: URL to the media.
    url: str
    #: Width of the media, if applicable.
    width: int | None
    #: Height of the media, if applicable.
    height: int | None
    #: Whether or not the media has its original dimensions.
    has_original_dimensions: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a media dict into a Media object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        return cls(
            type=data["type"],
            url=data["url"],
            width=data.get("width", None),
            height=data.get("height", None),
            has_original_dimensions=data.get("has_original_dimensions", False),
        )


class MediaList(list):
    """List of Media objects. Provides a convenience method for finding media of a specific size."""

    @property
    def no_dimensions(self) -> bool:
        """
        Check if the media in this list has no width/height.

        :returns: True if the media contained in the list is dimensionless,
        i.e. is not an image or video.
        """
        for media in self:
            if media.width is None or media.height is None:
                return True
        return False

    @property
    def original_dimensions(self) -> tuple[int, int] | None:
        """
        Get the original dimensions of the media, if present.

        :returns: Tuple of width and height, or None if original dimensions could
            not be determined.
        """
        if self.no_dimensions:
            return None

        for media in self:
            if media.has_original_dimensions:
                return (media.width, media.height)
        return None

    def get_hq(self) -> Media | None:
        """
        Find the highest-quality Media object.

        Returns either the media with original dimensions or the largest available
        media.

        :returns: Media object representing highest-quality media, or None if the list
            is empty.
        """
        if self.no_dimensions:
            return None

        _self_sorted = sorted(self, key=lambda m: m.width, reverse=True)

        for media in _self_sorted:
            if media.has_original_dimensions:
                return media

        return _self_sorted[0]

    def get_by_width(self, target_width: int) -> Media | None:
        """
        Find the closest Media object that fits the given width.

        :param target_width: Width to target.
        :returns: A matching Media object, or None if the list is empty.
        """
        if self.no_dimensions:
            return None

        _self_sorted = sorted(self, key=lambda m: m.width, reverse=True)

        for media in _self_sorted:
            if media.width <= target_width:
                return media

        return _self_sorted[-1]

    @classmethod
    def from_list_of_dicts(cls, data: list) -> Self:
        """Convert a list of media dicts to a MediaList."""
        out = cls()

        for m_data in data:
            out.append(Media.from_dict(m_data))

        return out


##
# Attribution data
# https://www.tumblr.com/docs/npf#attributions
##


@dataclass
class Attribution:
    """Contains attribution information for an image or other media."""

    type: ClassVar[str]

    @classmethod
    def from_dict(cls, data: dict) -> "Attribution":
        """
        Turn an attribution dict into an Attribution object by picking the correct
        attribution type to use.

        In subclasses, this method should convert the dict to the given type,
        or raise an exception if the type doesn't match.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        if data["type"] in ATTRIBUTION_TYPES:
            return ATTRIBUTION_TYPES[data["type"]].from_dict(data)
        raise NPFParseError("Unknown attribution type {data.get('type')}]}")

    def to_html(self) -> str:
        """
        Convert the attribution data to a human-viewable HTML format.

        To be implemented by subclasses.

        :returns: The conversion result, as a string containing valid HTML.
        """
        raise NotImplementedError

    def to_markdown(self) -> str:
        """
        Convert the attribution data to a human-viewable Markdown format.

        To be implemented by subclasses.

        :returns: The conversion result.
        """
        raise NotImplementedError


@dataclass
class AttributionApp(Attribution):
    """Attribution to an external app."""

    type: ClassVar[str] = "app"

    #: The URL to be attributed.
    url: str
    #: Name of the app.
    app_name: str | None = None
    #: Additional text to display.
    display_text: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn the attibution entry into an AttributionApp object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        return cls(
            url=data["url"],
            app_name=data.get("app_name", None),
            display_text=data.get("display_text", None),
        )

    def to_html(self) -> str:
        """
        Convert the attribution data to a human-viewable HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        caret_tag = '<span class="attribution-go-icon"><svg xmlns="http://www.w3.org/2000/svg" height="14" width="14" role="presentation"><use href="#managed-icon__caret-fat"></use></svg></span>'

        if self.app_name and self.display_text and self.app_name != "Twitter":
            text = self.app_name + " | " + self.display_text
        elif self.display_text:
            text = self.display_text
        elif self.app_name:
            text = self.app_name
        else:
            text = urllib.parse.urlparse(self.url).netloc

        return f'<div class="attribution app-attribution"><a href="{safe_url(self.url)}">{text}</a>{caret_tag}</div>'

    def to_markdown(self) -> str:
        """
        Convert the attribution data to a human-viewable Markdown format.

        :returns: The conversion result.
        """
        if self.app_name and self.display_text and self.app_name != "Twitter":
            text = self.app_name + " | " + self.display_text
        elif self.display_text:
            text = self.display_text
        elif self.app_name:
            text = self.app_name
        else:
            text = urllib.parse.urlparse(self.url).netloc
        return f"(from app: {text})"


@dataclass
class AttributionBlog(Attribution):
    """Attribution to a Tumblr blog."""

    type: ClassVar[str] = "blog"

    #: The URL of the blog to be attributed.
    url: str
    #: The blog to attribute.
    blog: "Blog"

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn the attibution entry into an AttributionBlog object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        from .types import Blog

        return cls(url=data["url"], blog=Blog.from_api(data["blog"]))

    def to_html(self) -> str:
        """
        Convert the attribution data to a human-viewable HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        return f'<div class="attribution blog-attribution"><a href="{safe_url(self.url)}">{self.blog.name}</a></div>'


@dataclass
class AttributionLink(Attribution):
    """Attribution to an external link."""

    type: ClassVar[str] = "link"

    #: The URL to be attributed.
    url: str

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn the attibution entry into an AttributionLink object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        return cls(
            url=data["url"],
        )

    def to_html(self) -> str:
        """
        Convert the attribution data to a human-viewable HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        caret_tag = '<span class="attribution-go-icon"><svg xmlns="http://www.w3.org/2000/svg" height="14" width="14" role="presentation"><use href="#managed-icon__caret-fat"></use></svg></span>'

        return f'<div class="attribution image-attribution"><a href="{safe_url(self.url)}">{urllib.parse.urlparse(self.url).netloc}</a>{caret_tag}</div>'

    def to_markdown(self) -> str:
        """
        Convert the attribution data to a human-viewable Markdown format.

        :returns: The conversion result.
        """
        return f"(source: {urllib.parse.urlparse(self.url).netloc})"


@dataclass
class AttributionPost(Attribution):
    """Attribution to a Tumblr post."""

    type: ClassVar[str] = "post"

    #: The URL of the post to be attributed.
    url: str
    #: The blog which made the post.
    blog: "Blog"

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn the attibution entry into an AttributionPost object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        from .types import Blog

        return cls(url=data["url"], blog=Blog.from_api(data["blog"]))

    def to_html(self) -> str:
        """
        Convert the attribution data to a human-viewable HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        return f'<div class="attribution post-attribution"><a href="{safe_url(self.url)}">GIF by <b>{html.escape(self.blog.name)}</b></a></div>'

    def to_markdown(self) -> str:
        """
        Convert the attribution data to a human-viewable Markdown format.

        :returns: The conversion result.
        """
        return f"(GIF by {self.blog.name})"


#: Mapping of type strings to attribution classes.
ATTRIBUTION_TYPES: dict[str, type[Attribution]] = {
    "app": AttributionApp,
    "blog": AttributionBlog,
    "link": AttributionLink,
    "post": AttributionPost,
}


##
# Content blocks
##


@dataclass
class ContentBlock:
    """Base class for NPF content blocks."""

    #: Content block type; defined by subclasses.
    type: ClassVar[str]

    @classmethod
    def from_dict(cls, data: dict) -> "ContentBlock":
        """
        Turn a content block dict into a ContentBlock object by picking the correct
        content block type to use.

        In subclasses, this method should convert the dict to the given type,
        or raise an exception if the type doesn't match.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        if "type" not in data:
            return ContentBlockUnknown(msg="Malformed content block")
        elif data["type"] in CONTENT_BLOCK_TYPES:
            return CONTENT_BLOCK_TYPES[data["type"]].from_dict(data)
        else:
            return ContentBlockUnknown(
                msg=f'Unknown content block type "{data["type"]}"'
            )

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        To be implemented by subclasses.

        :returns: The conversion result, as a string containing valid HTML.
        """
        raise NotImplementedError

    def to_markdown(self) -> str:
        """
        Convert the block data to a human-viewable Markdown format.

        :returns: The conversion result.
        """
        raise NotImplementedError


class ContentTextSubtype(StrEnum):
    """Enum representing possible text block subtypes."""

    #: Intended for Post headings.
    heading1 = "heading1"
    #: Intended for section subheadings.
    heading2 = "heading2"
    #: Tumblr Official clients display this with a large cursive font.
    quirky = "quirky"
    #: Intended for short quotations, official Tumblr clients display this with a large serif font.
    quote = "quote"
    #: Intended for longer quotations or photo captions, official Tumblr clients indent this text block.
    indented = "indented"
    #: Intended to mimic the behavior of the Chat Post type, official Tumblr clients display this with a monospace font.
    chat = "chat"
    #: Intended to be an ordered list item prefixed by a number.
    ordered_list_item = "ordered-list-item"
    #: Intended to be an unordered list item prefixed with a bullet.
    unordered_list_item = "unordered-list-item"


class TextFormatType(StrEnum):
    """Available inline format types."""

    bold = "bold"
    italic = "italic"
    strikethrough = "strikethrough"
    small = "small"

    link = "link"
    mention = "mention"
    color = "color"


@dataclass(eq=True, frozen=True)
class TextFormat:
    """Represents an inline format entry in text blocks."""

    #: Start of the formatting range (inclusive)
    start: int
    #: End of the formatting range (exclusive)
    end: int

    #: Type of the format.
    type: TextFormatType

    #: Additional data for the format.
    data: frozendict

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a format entry into a TextFormat object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """

        # Prepare format type
        try:
            _type = TextFormatType(data["type"])
        except ValueError as e:
            raise NPFParseError(f"Unknown formatting type {data['type']}") from e

        # Prepare remaining data dict
        _data = data.copy()
        del _data["start"]
        del _data["end"]
        del _data["type"]
        if "blog" in _data:
            _data["blog"] = frozendict(_data["blog"])

        return cls(
            start=data["start"], end=data["end"], type=_type, data=frozendict(_data)
        )

    @property
    def html_wrapper(self) -> HTMLWrapper:
        """HTML opening and closing tags for this format."""
        if self.type == TextFormatType.bold:
            open_tag = "b"
        elif self.type == TextFormatType.italic:
            open_tag = "i"
        elif self.type == TextFormatType.strikethrough:
            open_tag = "strike"
        elif self.type == TextFormatType.small:
            open_tag = "small"
        elif self.type == TextFormatType.link:
            # self.url is not None for TextFormatType.link
            open_tag = f"a href={safe_url(self.url)}"  # type: ignore
        elif self.type == TextFormatType.mention:
            # self.blog is not None for TextFormatType.mention
            open_tag = f"a href={safe_url(self.blog['url'])}"  # type: ignore
        elif self.type == TextFormatType.color:
            open_tag = f'span style="color: {self.hex}"'
        else:
            open_tag = "span"

        close_tag = open_tag.split(" ", 1)[0]

        return HTMLWrapper(open=f"<{open_tag}>", close=f"</{close_tag}>")

    @property
    def markdown_wrapper(self) -> MarkdownWrapper:
        """Markdown opening and closing tags for this format."""
        if self.type == TextFormatType.bold:
            return MarkdownWrapper(open="**", close="**")
        elif self.type == TextFormatType.italic:
            return MarkdownWrapper(open="*", close="*")
        elif self.type == TextFormatType.strikethrough:
            return MarkdownWrapper(open="~", close="~")
        elif self.type == TextFormatType.link:
            # self.url is not None for TextFormatType.link
            return MarkdownWrapper(open="[", close=f"]({safe_url(self.url)})")  # type: ignore
        elif self.type == TextFormatType.mention:
            # self.blog is not None for TextFormatType.mention
            return MarkdownWrapper(open="[", close=f"]({safe_url(self.blog['url'])})")  # type: ignore

        # Other types do not have a direct Markdown counterpart.
        return MarkdownWrapper(open="*", close="*")

    @property
    def blog(self) -> frozendict | None:
        """Information about the mentioned blog (mention type only)."""
        if not self.type == TextFormatType.mention:
            return None
        return self.data["blog"]

    @property
    def url(self) -> str | None:
        """Target URL of the link (link type only)."""
        if not self.type == TextFormatType.link:
            return None
        return self.data["url"]

    @property
    def hex(self) -> str | None:
        """Hex color with # prefix (color type only)."""
        if not self.type == TextFormatType.color:
            return None
        return self.data["hex"]


@dataclass
class ContentBlockText(ContentBlock):
    """Text block representing a single paragraph of text."""

    type: ClassVar[str] = "text"

    #: Text inside the paragraph.
    text: str

    #: Subtype of the block.
    subtype: ContentTextSubtype | None = None

    #: Indentation level, for blocks with a list item subtype.
    #: For other subtypes, defaults to -1.
    indent_level: int = -1

    #: Formatting data.
    formatting: list[TextFormat] | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a text content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        if "subtype" in data:
            try:
                _subtype = ContentTextSubtype(data["subtype"])
            except ValueError as e:
                raise NPFParseError(
                    f"Unknown text block subtype {data['subtype']}"
                ) from e

        else:
            _subtype = None

        if _subtype in (
            ContentTextSubtype.unordered_list_item,
            ContentTextSubtype.ordered_list_item,
            ContentTextSubtype.indented,
        ):
            _indent_level = data.get("indent_level", 0)
        else:
            _indent_level = -1

        if "formatting" in data:
            _formatting = [TextFormat.from_dict(i) for i in data["formatting"]]
            _formatting.sort(key=lambda f: f.start)
            _formatting.sort(key=lambda f: f.end, reverse=True)
            # TODO: Fix up duplicate formats
        else:
            _formatting = None

        return cls(
            text=data["text"],
            subtype=_subtype,
            indent_level=_indent_level,
            formatting=_formatting,
        )

    def _apply_formats(self, text: str, wrapper: WrapperType) -> str:
        """Apply formatting to the given text."""
        if wrapper != WrapperType.HTML and wrapper != WrapperType.Markdown:
            raise ValueError("Internal error: Invalid wrapper type")

        if not self.formatting:
            return text

        out = ""

        open_formats: deque[TextFormat] = deque()  # Stack of currently open formats
        temp_closed: deque[TextFormat] = (
            deque()
        )  # Temporary stack used to store closed formats
        # when fixing up HTML close tags
        format_starts = defaultdict(list)  # character: list of formats
        format_ends = defaultdict(list)  # character: list of formats

        for fmt in self.formatting:
            format_starts[fmt.start].append(fmt)
            format_ends[fmt.end].append(fmt)

        def _wrapper(fmt: TextFormat) -> HTMLWrapper | MarkdownWrapper:
            """Get the wrapper for the format according to the passed type."""
            nonlocal wrapper
            if wrapper == WrapperType.HTML:
                return fmt.html_wrapper
            elif wrapper == WrapperType.Markdown:
                return fmt.markdown_wrapper

        n_char = 0  # Currently parsed character *in the original text*;
        # used to determine format position
        for n_char in range(len(self.text)):
            # Open formats that need starting
            for fmt in format_starts[n_char]:
                out += _wrapper(fmt).open
                open_formats.append(fmt)

            # Close formats that need ending
            if format_ends[n_char]:
                # First, close tags until we close all the formats that end
                # on this character
                _ends = set(format_ends[n_char])
                while not set(temp_closed).issuperset(_ends):
                    fmt = open_formats.pop()
                    temp_closed.append(fmt)
                    out += _wrapper(fmt).close

                # Then, only reopen the ones we closed on the way
                for f in _ends:
                    temp_closed.remove(f)

                while temp_closed:
                    fmt = temp_closed.pop()
                    out += _wrapper(fmt).open
                    open_formats.append(fmt)

                del _ends

            # For HTML, add HTML-escaped letter to output
            if wrapper == WrapperType.HTML:
                out += html.escape(self.text[n_char])
            else:
                out += self.text[n_char]

        # Close all remaining open formats
        while open_formats:
            fmt = open_formats.pop()
            out += _wrapper(fmt).close

        return out

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """

        if self.formatting:
            # If formatting is present, apply formats to the text
            out = self._apply_formats(self.text, WrapperType.HTML)

        else:
            # Otherwise, the output will simply be HTML-escaped
            # content.
            out = html.escape(self.text)

        # If the text length is exactly 0, turn this text into a newline.
        if len(out) == 0:
            if not self.subtype:
                return ""
            out = "<br>"

        # Apply subtype wrappers
        if self.subtype:
            if self.subtype == ContentTextSubtype.heading1:
                out = "<h1>" + out + "</h1>"
            elif self.subtype == ContentTextSubtype.heading2:
                out = "<h2>" + out + "</h2>"

            # Note that the <ul>/<ol> wrappers are applied in NPFPost.to_html().
            elif self.subtype == ContentTextSubtype.ordered_list_item:
                out = "<li>" + out + "</li>"
            elif self.subtype == ContentTextSubtype.unordered_list_item:
                out = "<li>" + out + "</li>"

            elif self.subtype == ContentTextSubtype.chat:
                out = '<p class="npf_chat">' + out + "</p>"
            elif self.subtype == ContentTextSubtype.quote:
                out = '<p class="npf_quote">' + out + "</p>"
            elif self.subtype == ContentTextSubtype.quirky:
                out = '<p class="npf_quirky">' + out + "</p>"

            else:
                out = "<p>" + out + "</p>"

        # Apply emoji styling. (The use of self.text instead of out is deliberate;
        # it means that formatting tags are ignored.)
        elif len(self.text) > 0 and not self.text[0].isalnum():
            # mypy misdetects emoji.analyze as not being real
            emoji_tuple = tuple(itertools.islice(emoji.analyze(self.text), 4))  # type: ignore
            emoji_and_char_tuple = tuple(
                itertools.islice(emoji.analyze(self.text, non_emoji=True), 4)  # type: ignore
            )
            if len(emoji_tuple) <= 3 and [e.chars for e in emoji_tuple] == [
                e.chars for e in emoji_and_char_tuple
            ]:
                out = '<p class="emoji-large">' + out + "</p>"
            else:
                out = "<p>" + out + "</p>"

        else:
            out = "<p>" + out + "</p>"

        return out

    def to_markdown(self) -> str:
        """
        Convert the block data to a human-viewable Markdown format.

        :returns: The conversion result.
        """

        out: str = ""

        if self.formatting:
            # If formatting is present, apply formats to the text
            out = self._apply_formats(self.text, WrapperType.Markdown)

        else:
            # Otherwise, the output will simply be the raw text
            out = self.text

        # If the text length is exactly 0, turn this text into a newline.
        if len(out) == 0:
            out = "\n"

        # Apply subtype wrappers
        if self.subtype:
            indent_spacing = "  " * self.indent_level

            if self.subtype == ContentTextSubtype.heading1:
                out = "# " + out
            elif self.subtype == ContentTextSubtype.heading2:
                out = "## " + out

            # TODO: We don't have a way to determine which list item this is
            # at block level.
            elif self.subtype == ContentTextSubtype.ordered_list_item:
                out = indent_spacing + "#. " + out.replace("\n", "\n" + indent_spacing)
            elif self.subtype == ContentTextSubtype.unordered_list_item:
                out = indent_spacing + "* " + out.replace("\n", "\n" + indent_spacing)
            elif self.subtype == ContentTextSubtype.quote:
                out = (
                    indent_spacing
                    + "> "
                    + out.replace("\n", "\n" + indent_spacing + "> ")
                )

        return out


@dataclass
class ContentBlockLink(ContentBlock):
    """Represents a large link box."""

    type: ClassVar[str] = "link"

    #: Target URL of the link.
    url: str

    title: str | None = None
    description: str | None = None
    author: str | None = None
    site_name: str | None = None
    display_url: str | None = None
    poster: MediaList | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a link content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        if "poster" in data and data["poster"]:
            _poster = MediaList.from_list_of_dicts(data["poster"])
        else:
            _poster = None

        return cls(
            url=data["url"],
            title=data.get("title", None),
            description=data.get("description", None),
            author=data.get("author", None),
            site_name=data.get("site_name", None),
            display_url=data.get("display_url", None),
            poster=_poster,
        )

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        if self.title:
            title = html.escape(self.title)
        elif self.display_url:
            title = html.escape(self.display_url)
        else:
            title = html.escape(self.url)

        out = '<div class="link-embed">'

        if self.poster:
            selected_size_poster = self.poster.get_by_width(640)
            if selected_size_poster:
                out += f'<div class="link-embed-image-top"><img src="{safe_url(selected_size_poster.url)}" class="link-image"><span class="link-image-title">{title}</span></div>'
            else:
                out += f'<div class="link-embed-top"><span class="link-title">{title}</span></div>'
        else:
            out += f'<div class="link-embed-top"><span class="link-title">{title}</span></div>'

        out += '<div class="link-embed-bottom">'
        if self.description:
            out += (
                f'<span class="link-description">{html.escape(self.description)}</span>'
            )
        if self.site_name:
            out += f'<span class="link-sitename">{html.escape(self.site_name)}</span>'
        out += "</div></div>"

        return out

    def to_markdown(self) -> str:
        """
        Convert the block data to a human-viewable Markdown format.

        :returns: The conversion result.
        """
        if self.title:
            title = self.title
        elif self.display_url:
            title = self.display_url
        else:
            title = self.url

        out = f"> [{title}]({self.url})"
        if self.description:
            out += f"\n> {self.description}"

        return out


@dataclass
class ContentBlockImage(ContentBlock):
    """Represents an image."""

    type: ClassVar[str] = "image"

    #: MediaList containing Media objects representing different size of the image.
    media: MediaList

    #: Attribution for the image.
    attribution: Attribution | None = None

    #: Alt text, if any.
    alt_text: str | None = None
    #: Caption, if any.
    caption: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn an image content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        if "attribution" in data:
            _attribution = Attribution.from_dict(data["attribution"])
        else:
            _attribution = None

        return cls(
            media=MediaList.from_list_of_dicts(data.get("media", [])),
            attribution=_attribution,
            alt_text=data.get("alt_text", None),
            caption=data.get("caption", None),
        )

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        media_orig = self.media.get_hq()
        media_small = self.media.get_by_width(640)

        if not media_orig or not media_small or not media_orig.width:
            return "<p>(broken image)</p>"

        badge_tag = ""
        if ".gif" in media_small.url:
            badge_tag = '<span class="tmblr-alt-text-helper">GIF</span>'
        elif self.alt_text:
            badge_tag = '<span class="tmblr-alt-text-helper">ALT</span>'

        classes = "tmblr-full"
        if media_orig.width < 300:
            classes += " orig-size"
        if ".gif" in media_small.url:
            classes += " gif"

        figure_tag = f'<figure class="{classes}"><img src="{safe_url(media_small.url)}"/>{badge_tag}</figure>'

        if self.attribution:
            figure_tag += self.attribution.to_html()

        return figure_tag

    def to_markdown(self) -> str:
        """
        Convert the block data to a human-viewable Markdown format.

        :returns: The conversion result.
        """

        # Markdown does support images... but let me tell you a secret.
        # This isn't actually Markdown. It's just sparkling plaintext.
        # We use this for plaintext descriptions in embeds, which do not
        # support embedding images, so we use a placeholder instead.

        return "(image)"


@dataclass
class ContentBlockVideo(ContentBlock):
    """Represents a video embed."""

    type: ClassVar[str] = "video"

    media: Media | None
    poster: MediaList | None
    url: str | None

    alt_text: str | None = None
    attribution: Attribution | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a video content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        if "media" in data and data["media"]:
            media = Media.from_dict(data["media"])
        else:
            media = None

        # Get thumbnail (poster) of the video.
        if "poster" in data:
            poster = MediaList.from_list_of_dicts(data["poster"])

        # If there is no poster object, it's still possible to get the thumbnail
        # URL by modifying the URL.
        elif media:
            poster_url = (
                urllib.parse.urlparse(media.url)
                ._replace(netloc="64.media.tumblr.com")
                .geturl()
                .replace(".mp4", "_frame1.jpg")
                .replace("_720_frame1", "_frame1")
            )

            poster = MediaList()
            poster.append(
                Media(
                    type="image/jpg",
                    url=poster_url,
                    width=media.width,
                    height=media.height,
                )
            )

        else:
            poster = None

        if "attribution" in data:
            attribution = Attribution.from_dict(data["attribution"])
        else:
            attribution = None

        return cls(
            url=data.get("url", None),
            media=media,
            poster=poster,
            alt_text=data.get("alt_text", None),
            attribution=attribution,
        )

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        if self.poster:
            poster = self.poster.get_by_width(640)
            if poster:
                poster_img_tag = (
                    f'<img class="video-poster" src="{safe_url(poster.url)}"/>'
                )
        else:
            poster_img_tag = '<div class="video-poster video-poster-dummy"></div>'

        play_button_tag = '<span class="tmblr-play-button-helper"><svg xmlns="http://www.w3.org/2000/svg" height="32" width="32" role="presentation" style="--icon-color-primary: RGB(255, 255, 255);"><use href="#managed-icon__play-cropped"></use></svg></span>'

        alt_tag = ""
        if self.alt_text:
            alt_tag = '<span class="tmblr-alt-text-helper">ALT</span>'

        figure_tag = f'<figure class="tmblr-full video-block">{poster_img_tag}{play_button_tag}{alt_tag}</figure>'

        if self.attribution:
            figure_tag += self.attribution.to_html()

        return figure_tag

    def to_markdown(self) -> str:
        """
        Convert the block data to a human-viewable Markdown format.

        :returns: The conversion result.
        """

        # See note about images; this is an identical situation.
        # This is meant as a placeholder.

        return "(video)"


@dataclass
class ContentBlockAudio(ContentBlock):
    """Represents an audio embed."""

    type: ClassVar[str] = "audio"

    provider: str | None = None

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    poster: MediaList | None = None
    media: Media | None = None
    alt_text: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn an audio content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        if "poster" in data:
            poster = MediaList.from_list_of_dicts(data["poster"])
        else:
            poster = None

        if "media" in data:
            media = Media.from_dict(data["media"])
        else:
            media = None

        return cls(
            title=data.get("title"),
            artist=data.get("artist"),
            album=data.get("album"),
            alt_text=data.get("alt_text"),
            poster=poster,
            media=media,
            provider=data.get("provider"),
        )

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        # This returns a (nonfunctional) official client-like view of an
        # audio track.
        selected_size_poster = None
        if self.poster:
            selected_size_poster = self.poster.get_by_width(85)
        poster_url = ""
        if selected_size_poster:
            poster_url = selected_size_poster.url

        out = f'<div class="audio-player{" audio-" + self.provider if self.provider else ""}">'

        # Play button/service icon
        out += f'<div class="play-button"><svg xmlns="http://www.w3.org/2000/svg" height="24" width="24" role="presentation" style="--icon-color-primary: RGB(var(--white));"><use href="#managed-icon__{self.provider if self.provider in ("spotify", "soundcloud") else "play-cropped"}"></use></svg></div>'

        # Audio info
        out += '<div class="audio-info">'
        if self.title:
            out += f'<div class="title">{html.escape(self.title)}</div>'
        if self.artist:
            out += f'<div class="artist">{html.escape(self.artist)}</div>'
        if self.album:
            out += f'<div class="album">{html.escape(self.album)}</div>'
        out += "</div>"

        if poster_url:
            out += f'<div class="audio-image"><img src="{safe_url(poster_url)}"></div>'
        out += "</div>"

        return out

    def to_markdown(self) -> str:
        """
        Convert the block data to a human-viewable Markdown format.

        :returns: The conversion result.
        """

        return "(audio)"


@dataclass
class PollAnswer:
    """The answer to a poll represented by ContentBlockPoll."""

    #: ID of the answer; used to correlate the answer to the vote count returned
    #: by the poll results API.
    client_id: str

    #: Displayed text of the answer.
    answer_text: str

    #: Amount of votes, or None if the information hasn't been fetched yet.
    #: See ContentBlockPoll.fetch_results().
    votes: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Turn a poll answer object into a PollAnswer."""
        return cls(client_id=data["client_id"], answer_text=data["answer_text"])


@dataclass
class ContentBlockPoll(ContentBlock):
    """Represents a poll."""

    type: ClassVar[str] = "poll"

    #: ID of the poll; used to fetch poll result data.
    client_id: str

    #: Question asked in the poll.
    question: str

    #: Poll answers.
    answers: list[PollAnswer]

    #: Date of poll creation.
    created_at: str

    #: Whether or not the poll allows for multiple choices.
    multiple_choice: bool

    #: Amount of seconds since poll creation until its closure.
    expire_after: int

    #: Results of the poll, or None if they haven't been fetched yet.
    #: Poll results are fetched from the API separately.
    results: Union["PollResults", None] = None

    #: Total amount of votes, or None if poll results haven't been fetched yet.
    total_votes: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a poll content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        return cls(
            client_id=data["client_id"],
            question=data["question"],
            answers=[PollAnswer.from_dict(a) for a in data["answers"]],
            created_at=data["created_at"],
            multiple_choice=data["settings"]["multiple_choice"],
            expire_after=data["settings"]["expire_after"],
        )

    async def fetch_results(
        self, api: "TumblrAPI", blog_id: str, post_id: int, skip_cache: bool = False
    ):
        """
        Fill in post result data from the poll results API.

        Poll results are accessible through a separate API, but accessing it
        requires information that is not typically available at block level.
        This function can be called from the post level to fill in result
        information.

        (Note that TumblrAPI.get_post() already calls this function automatically
        for all polls within the post, unless the fetch_polls option is set to
        False.)

        :param api: Instance of TumblrAPI to use
        :param blog_id: Blog identifier: username, URL or ID.
        :param post_id: Post ID.
        :param skip_cache: If True, skips the cache unconditionally.
        :raises NPFParseError: if poll data is not available.
        """
        results = await api.get_poll_results(
            blog_id, post_id, self.client_id, skip_cache=skip_cache
        )
        if not results:
            raise NPFParseError("Poll data not found")

        self.results = results

        total_votes = 0

        for answer in self.answers:
            votes = results.results[answer.client_id]
            answer.votes = votes
            total_votes += votes

        self.total_votes = total_votes

    @cached_property
    def created_at_dt(self) -> datetime.datetime:
        """Poll creation date as a datetime object."""
        return dateutil.parser.parse(self.created_at)

    @cached_property
    def expire_delta(self) -> datetime.timedelta:
        """Time delta for poll expiry."""
        return datetime.timedelta(seconds=self.expire_after)

    @cached_property
    def end_time_dt(self) -> datetime.datetime:
        """Time at which the poll ends."""
        return self.created_at_dt + self.expire_delta

    def is_over(self) -> bool:
        """Check whether or not the poll is closed."""
        now = datetime.datetime.now(datetime.timezone.utc)

        return self.end_time_dt < now

    @property
    def remaining_time_str(self) -> str:
        """Human-readable representation of the remaining time."""

        # Get creation date
        created_at = dateutil.parser.parse(self.created_at)
        expire_delta = datetime.timedelta(seconds=self.expire_after)
        end_time = created_at + expire_delta
        now = datetime.datetime.now(datetime.timezone.utc)

        #: Human-readable "time left" string
        time_str = ""

        if end_time >= now:
            time_remaining = end_time - now

            # https://stackoverflow.com/questions/14190045/how-do-i-convert-datetime-timedelta-to-minutes-hours-in-python
            days, seconds = time_remaining.days, time_remaining.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60

            if days > 0:
                time_str = f"Remaining time: {days} days {hours} hours"
            else:
                time_str = f"Remaining time: {hours} hours {minutes} minutes"

        else:
            time_str = "Final result"

        return time_str

    @property
    def total_votes_str(self) -> str:
        """Total votes as a pluralized string."""
        return f"{self.total_votes:,} vote{'s' if self.total_votes != 1 else ''}"

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        is_over = self.is_over()

        if self.results:
            most_votes = max(self.results.results.values())

        out = f'<div class="poll-block{" poll-over" if is_over else ""}"><span class="poll-question">{html.escape(self.question)}</span>'

        # Generate poll answer divs
        if is_over:
            for answer in self.answers:
                if self.results:
                    answer_count = self.results.results[answer.client_id]
                    if self.total_votes:
                        _answer_percentage = (answer_count / self.total_votes) * 100
                        answer_percentage = (
                            "{:.2f}".format(_answer_percentage)
                            if not str(_answer_percentage).endswith(".0")
                            else str(int(_answer_percentage))
                        )
                    else:
                        answer_percentage = "0"
                else:
                    answer_count = 0
                    answer_percentage = "0"
                out += f'<div class="poll-answer{" poll-answer-win" if answer_count == most_votes else ""}"><div class="poll-answer-filler" style="width: {answer_percentage}%;"></div><span class="poll-answer-text">{html.escape(answer.answer_text)}</span><span class="poll-answer-percentage">{answer_percentage}%</span></div>'
        else:
            for answer in self.answers:
                out += (
                    f'<div class="poll-answer">{html.escape(answer.answer_text)}</div>'
                )

        out += f'<span class="poll-meta">{self.total_votes_str} · {self.remaining_time_str}</span></div>'

        return out

    def to_markdown(self) -> str:
        """
        Convert the block data to a human-viewable Markdown format.

        :returns: The conversion result.
        """

        out = f"### {self.question}"

        for answer in self.answers:
            if self.results:
                answer_count = self.results.results[answer.client_id]
                if self.total_votes:
                    _answer_percentage = (answer_count / self.total_votes) * 100
                    answer_percentage = (
                        "{:.2f}".format(_answer_percentage)
                        if not str(_answer_percentage).endswith(".0")
                        else str(int(_answer_percentage))
                    )
                else:
                    answer_percentage = "0"
            else:
                answer_percentage = "0"

            out += f"\n* [ ] {answer.answer_text} ({answer_percentage}%)"

        out += f"\n*({self.total_votes_str} · {self.remaining_time_str})*"

        return out


@dataclass
class ContentBlockUnknown(ContentBlock):
    """Represents an unknown content block."""

    type: ClassVar[str] = "unknown"

    #: An optional message to include in the block.
    msg: str | None = None

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        return '<span class="unknown-block">Unknown block type. Please open an issue at https://github.com/knuxify/fxtumblr and link this post.</span>'

    def to_markdown(self) -> str:
        """
        Convert the block data to a human-viewable Markdown format.

        :returns: The conversion result.
        """

        return "Unknown block type. Please open an issue at https://github.com/knuxify/fxtumblr and link this post."


#: Mapping of type strings to content block classes.
CONTENT_BLOCK_TYPES: dict[str, type[ContentBlock]] = {
    "text": ContentBlockText,
    "image": ContentBlockImage,
    "link": ContentBlockLink,
    "video": ContentBlockVideo,
    "audio": ContentBlockAudio,
    "poll": ContentBlockPoll,
}


##
# Layout blocks
##


@dataclass
class LayoutBlock:
    """Base class for NPF layout blocks."""

    #: Layout block type; defined by subclasses.
    type: ClassVar[str]

    @classmethod
    def from_dict(cls, data: dict) -> "LayoutBlock":
        """
        Turn a layout block dict into a LayoutBlock object by picking the correct
        layout block type to use.

        In subclasses, this method should convert the dict to the given type,
        or raise an exception if the type doesn't match.

        :param data: Data to use for object creation.
        :raises NPFParseError: If the layout type is unknown or the data is invalid.
        :returns: The resulting object.
        """
        if "type" not in data:
            raise NPFParseError("Invalid layout block")
        elif data["type"] == "rows":
            return LayoutBlockRows.from_dict(data)
        elif data["type"] == "ask":
            return LayoutBlockAsk.from_dict(data)
        raise NPFParseError("Unknown layout block")


class RangedLayoutBlock:
    """
    Mixin for declaring a subset of layout blocks that cover
    multiple blocks.
    """

    #: List of block indeces covered by the layout, counting from 0.
    blocks: list[int]

    @property
    def html_wrapper(self) -> HTMLWrapper:
        """Generate a HTMLWrapper object containing HTML wrappers for this layout."""
        raise NotImplementedError

    @property
    def markdown_wrapper(self) -> MarkdownWrapper:
        """Generate a MarkdownWrapper object containing Markdown wrappers for this layout."""
        raise NotImplementedError


@dataclass
class LayoutDisplay:
    """A single element of the display dict in LayoutBlockRows."""

    #: List of block indeces covered by the block, starting from 0.
    blocks: list[int]

    #: Mode, currently unused.
    mode: str = "weighted"

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a display dict into a LayoutDisplay object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        return cls(blocks=data["blocks"], mode=data.get("mode", "weighted"))


@dataclass
class LayoutBlockRows(LayoutBlock):
    """Row-based layout."""

    type: ClassVar[str] = "rows"

    #: List of LayoutDisplay objects representing the block display data.
    display: list[LayoutDisplay]

    #: If not None, represents the amount of blocks before a truncation block
    #: ("Read More...") must be shown.
    truncate_after: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a rows layout block dict into a LayoutBlockRows object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        return cls(
            display=[LayoutDisplay.from_dict(d) for d in data["display"]],
            truncate_after=data.get("truncate_after", None),
        )


@dataclass
class LayoutBlockAsk(LayoutBlock, RangedLayoutBlock):
    """Layout element representing an asked question."""

    type: ClassVar[str] = "ask"

    #: List of block indeces covered by the block, counting from 0.
    blocks: list[int]

    #: Attribution of the question, or None if the question is anonymous.
    attribution: Attribution | None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn an ask layout block dict into a LayoutBlockRows object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        if "attribution" in data:
            attribution = Attribution.from_dict(data["attribution"])
        else:
            attribution = None

        return cls(
            blocks=data["blocks"],
            attribution=attribution,
        )

    @property
    def html_wrapper(self) -> HTMLWrapper:
        """Generate a HTMLWrapper object containing HTML wrappers for this layout."""
        if self.attribution and isinstance(self.attribution, AttributionBlog):
            return HTMLWrapper(
                open=f'<div class="question"><div class="question-header"><strong class="asking-name">{html.escape(self.attribution.blog.name)}</strong> asked:</div><div class="question-content">',
                close="</div></div>",
            )
        else:
            return HTMLWrapper(
                open='<div class="question"><div class="question-header"><strong class="asking-name">Anonymous</strong> asked:</div><div class="question-content">',
                close="</div></div>",
            )

    @property
    def markdown_wrapper(self) -> MarkdownWrapper:
        """Generate a MarkdownWrapper object containing Markdown wrappers for this layout."""
        if self.attribution and isinstance(self.attribution, AttributionBlog):
            return MarkdownWrapper(
                open=f"💬 {self.attribution.blog.name} asked:", close=""
            )
        else:
            return MarkdownWrapper(open="💬 Anonymous asked:\n\n", close="")


##
# Meta layouts (fxtumblr-specific, used to wrap multiple blocks)
##


@dataclass
class MetaLayoutMultiBlockRow(LayoutBlock, RangedLayoutBlock):
    """
    Wrapper for a row that contains multiple blocks.

    These are typically represented by a LayoutDisplay object with more than one
    block; we wrap them in a meta layout to make it easier to re-use the code
    we have for wrapping asks.
    """

    type: ClassVar[str] = "multi_block_row"

    #: List of block indeces covered by the block, counting from 0.
    blocks: list[int]

    @property
    def html_wrapper(self) -> HTMLWrapper:
        """Generate a HTMLWrapper object containing HTML wrappers for this layout."""
        return HTMLWrapper(
            open=f'<div class="row-multiple row-{len(self.blocks)}">',
            close="</div>",
        )

    @property
    def markdown_wrapper(self) -> MarkdownWrapper:
        """Generate a MarkdownWrapper object containing Markdown wrappers for this layout."""
        return MarkdownWrapper(open="", close="")


#: HTMLWrapper objects for indented text block subtypes.
INDENTED_BLOCK_WRAPPERS: dict[ContentTextSubtype, HTMLWrapper] = {
    ContentTextSubtype.unordered_list_item: HTMLWrapper(
        open='<ul class="text-list">',
        close="</ul>",
        up="<li>",
        down="</li>",
    ),
    ContentTextSubtype.ordered_list_item: HTMLWrapper(
        open='<ol class="text-list">',
        close="</ol>",
        up="<li>",
        down="</li>",
    ),
    ContentTextSubtype.indented: HTMLWrapper(
        open='<blockquote class="text-block text-indented">',
        close="</blockquote>",
        up="",
        down="",
    ),
}


##
# Post parsing
##


def _update_indented_block_wrappers(
    indent_stack: list[ContentBlockText], block: ContentBlock
) -> str:
    """
    Given a stack of currently opened indents and a new block to parse,
    generate opening/closing tags and update the stack.

    Internal function for npf_to_html.

    :param indent_stack: List of ContentBlockText objects representing currently
        opened tags.
    :param block: ContentBlock for the currently parsed block.
    :returns: HTML string containing opening/closing tags.
    """
    out = ""

    def _pop():
        """Remove an item off the top of the indent stack."""
        nonlocal indent_stack
        nonlocal out
        indent_block = indent_stack.pop()
        wrapper = INDENTED_BLOCK_WRAPPERS[indent_block.subtype]
        if indent_block.indent_level > 0:
            wrapper_outer = INDENTED_BLOCK_WRAPPERS[indent_stack[-1].subtype]
            out += wrapper.close + wrapper_outer.down
        else:
            out += wrapper.close

    def _open(block: ContentBlockText):
        """Add an item to the top of the indent stack."""
        nonlocal indent_stack
        nonlocal out

        # Added for mypy reasons; these two conditions are indirectly
        # guaranteed to be true by the outer function (we only consider items
        # with an indent_level >= 0, which is only true for blocks with a
        # subtype within the list of indented block subtypes - see
        # ContentBlockText.from_dict().)
        if not block.subtype or (indent_stack and not indent_stack[-1].subtype):
            return

        wrapper = INDENTED_BLOCK_WRAPPERS[block.subtype]
        if len(indent_stack) > 0 and indent_stack[-1].subtype:
            indent_wrapper = INDENTED_BLOCK_WRAPPERS[indent_stack[-1].subtype]
            out += indent_wrapper.up + wrapper.open
        else:
            out += wrapper.open
        indent_stack.append(block)

    if not isinstance(block, ContentBlockText) or block.indent_level < 0:
        # Current block is not a text block or has no indent; close all indents
        while indent_stack:
            _pop()

    else:
        # Current block is indented.

        if indent_stack:
            # If there already are opened indented blocks:
            curr_indent: int = len(indent_stack) - 1
            target_indent: int = block.indent_level
            indent_delta: int = target_indent - curr_indent

            if indent_delta > 0:
                # We need to open tags to get to our desired indent level.
                while indent_delta > 0:
                    _open(block)
                    indent_delta -= 1

            elif indent_delta < 0:
                # We need to close tags to get to our desired indent level.
                while indent_delta < 0:
                    _pop()
                    indent_delta += 1

            else:  # indent_delta == 0
                if indent_stack[-1].subtype != block.subtype:
                    # If the subtype of the previous indented block and current
                    # block don't match, we close the previous item and open the
                    # new one.
                    _pop()
                    _open(block)

        else:
            # If there are no opened indented blocks, just open the new one.
            _open(block)

    return out


def _parse_layouts(
    layouts: list[LayoutBlock],
    content: list[ContentBlock] | None = None,
    truncate: bool = True,
) -> tuple[
    list[int],
    dict[int, list[RangedLayoutBlock]],
    dict[int, list[RangedLayoutBlock]],
    bool,
]:
    """
    Parse a list of layouts and determine block order, layout start/end points
    and whether the layout is truncated.

    :param layouts: List of LayoutBlock objects representing layout blocks.
    :param truncate: Whether or not to add the "read more" block after the
        cutoff passed in the truncate_after variable of the rows layout.
        For posts without a truncate_after setting, this option does nothing.
    :returns: Tuple with 4 elements:
        - block_order: list[int] - list of block indeces
        - layout_starts: dict[int, list[RangedLayoutBlock]] - list of start points
          of ranged layouts
        - layout_ends: dict[int, list[RangedLayoutBlock]] - list of end points
          of ranged layouts
        - is_truncated: if True, the post is truncated
    """

    # The following lists contain start and end indeces for layouts;
    # the indeces refer to the index of the block in block_order (defined
    # below), which is not necessarily the same as the index in content
    # (as the NPF docs permit listing blocks out-of-order in multi-block rows).
    layout_starts: dict[int, list[RangedLayoutBlock]] = defaultdict(list)
    layout_ends: dict[int, list[RangedLayoutBlock]] = defaultdict(list)

    # Calculate block order based on LayoutBlockRows.
    found_rows: bool = False
    is_truncated: bool = False
    block_order: list[int] = []
    for layout in layouts:
        if isinstance(layout, LayoutBlockRows):
            found_rows = True

            for display in layout.display:
                block_order += display.blocks

                # For conversion convenience, we turn multi-block rows
                # into their own layouts.
                if len(display.blocks) > 1:
                    multi_block_row = MetaLayoutMultiBlockRow(blocks=display.blocks)
                    layout_starts[len(block_order) - len(display.blocks)].append(
                        multi_block_row
                    )
                    layout_ends[len(block_order) - 1].append(multi_block_row)

                # If truncation is enabled, stop adding new blocks after
                # this point, and mark the post as truncated
                if (
                    truncate
                    and layout.truncate_after
                    and len(block_order) > layout.truncate_after
                ):
                    is_truncated = True
                    break

            break

    # Per Tumblr docs: if there is no rows layout, assume rows with one block
    # each
    if not found_rows and content is not None:
        block_order = list(range(len(content)))

    # 2. Set layout starts/ends for non-row layout blocks.
    # (We can only do this after block_order has been filled.)
    for layout in layouts:
        if isinstance(layout, LayoutBlockRows):
            continue

        if isinstance(layout, RangedLayoutBlock):
            layout_starts[block_order.index(layout.blocks[0])].append(layout)
            layout_ends[block_order.index(layout.blocks[-1])].append(layout)

    return block_order, layout_starts, layout_ends, is_truncated


def npf_to_html(
    content: list[ContentBlock], layouts: list[LayoutBlock], truncate: bool = True
) -> str:
    """
    Given a list of content blocks and layouts, convert NPF data to HTML.

    :param content: List of ContentBlock objects representing content blocks.
    :param layouts: List of LayoutBlock objects representing layout blocks.
    :param truncate: Whether or not to add the "read more" block after the
        cutoff passed in the truncate_after variable of the rows layout.
        For posts without a truncate_after setting, this option does nothing.
    :returns: Valid HTML representation of the data.
    """

    # 1. Parse layouts to get block order and layouts
    block_order, layout_starts, layout_ends, is_truncated = _parse_layouts(
        layouts=layouts, content=content, truncate=truncate
    )

    # 2. Iterate over all content blocks and convert them into HTML.
    out: str = ""
    i: int = 0  # index in block_index
    indent_stack: list[
        ContentBlockText
    ] = []  # stack of ContentBlockText objects for indented text blocks
    for block_index in block_order:
        try:
            block = content[block_index]
        except IndexError as e:
            raise NPFParseError(
                "Invalid layout; content block index out of range"
            ) from e

        # 3.1. If layouts start, open them.
        for _layout in layout_starts[i]:
            out += _layout.html_wrapper.open

        # 3.2. If there's a list block, call some function to determine what
        # tags to place, and place the list wrappers in a stack.
        out += _update_indented_block_wrappers(indent_stack, block)

        # 3.3. Add the block content.
        # 3.3.1. If we're dealing with a text block but aren't in an indent,
        #        add <div class="text-block"> wrapper.
        if not indent_stack and isinstance(block, ContentBlockText):
            out += '<div class="text-block">' + block.to_html() + "</div>"
        else:
            out += block.to_html()

        # 3.4. If layouts end, close them.
        if layout_ends[i]:
            # 3.4.1. If indented blocks are open, close them first.
            while indent_stack:
                indent_block = indent_stack.pop()
                assert indent_block.subtype
                wrapper = INDENTED_BLOCK_WRAPPERS[indent_block.subtype]
                if indent_block.indent_level > 0:
                    out += wrapper.close + wrapper.down
                else:
                    out += wrapper.close

            # 3.4.2. Close the layouts.
            for _layout in layout_ends[i]:
                out += _layout.html_wrapper.close

        i += 1

    # 4. Close all opened indented blocks.
    while indent_stack:
        indent_block = indent_stack.pop()
        assert indent_block.subtype
        wrapper = INDENTED_BLOCK_WRAPPERS[indent_block.subtype]
        if indent_block.indent_level > 0:
            out += wrapper.close + wrapper.down
        else:
            out += wrapper.close

    # 5. If the post is truncated, add the "Read more" block.
    if is_truncated:
        out += '<div class="read-more">Keep reading</div>'

    # 6. Return the resulting string.
    return sanitize_html(out)


def npf_to_markdown(
    content: list[ContentBlock], layouts: list[LayoutBlock], truncate: bool = True
) -> str:
    """
    Given a list of content blocks and layouts, convert NPF data to a
    Markdown-like format.

    :param content: List of ContentBlock objects representing content blocks.
    :param content: List of LayoutBlock objects representing layout blocks.
    :param truncate: Whether or not to add the "read more" block after the
        cutoff passed in the truncate_after variable of the rows layout.
        For posts without a truncate_after setting, this option does nothing.
    :returns: Valid HTML representation of the data.
    """

    out = ""

    # 1. Parse layouts to get block order and layouts
    block_order, layout_starts, layout_ends, is_truncated = _parse_layouts(
        layouts=layouts, content=content, truncate=truncate
    )

    # 2. Convert all blocks to Markdown
    ordered_list_counts: dict[int, int] = {}
    in_ask: bool = False
    in_indented_block: bool = False
    prev_was_indented: bool = False
    for block_index in block_order:
        try:
            block = content[block_index]
        except IndexError as e:
            raise NPFParseError(
                "Invalid layout; content block index out of range"
            ) from e

        md = block.to_markdown()

        # If a layout opens, open it
        if layout_starts[block_index]:
            for layout in layout_starts[block_index]:
                if isinstance(layout, LayoutBlockAsk):
                    # If we enter an ask block, note it down. We need to put the
                    # ask content in a quote.
                    in_ask = True

                out += layout.markdown_wrapper.open

        if isinstance(block, ContentBlockText) and block.indent_level >= 0:
            # Custom parsing for ordered lists. Since we don't know the order of
            # list items at block level, we need to keep track of it here.
            if block.subtype == ContentTextSubtype.ordered_list_item:
                if block.indent_level not in ordered_list_counts:
                    ordered_list_counts[block.indent_level] = 1
                else:
                    ordered_list_counts[block.indent_level] += 1
                md = md.replace("#.", f"{ordered_list_counts[block.indent_level]}.", 1)

            in_indented_block = True

        else:
            # If we encounter a non-indented block, clear the ordered list item levels
            ordered_list_counts.clear()

            in_indented_block = False

        # Wrap ask content in a quote
        if in_ask:
            md = "> " + md.replace("\n", "\n> ")

        # Add newlines
        if (in_indented_block and prev_was_indented) or in_ask:
            out += "\n"
        else:
            out += "\n\n"

        out += md

        # If a layout closes, close it
        if layout_ends[block_index]:
            for layout in layout_ends[block_index]:
                if isinstance(layout, LayoutBlockAsk):
                    in_ask = False

                out += layout.markdown_wrapper.close

        prev_was_indented = in_indented_block

    return out.strip()


@dataclass
class NPFPost:
    """A single post in a trail."""

    id: int
    timestamp: int
    blog: "Blog"

    #: List of content blocks within the post.
    content: list[ContentBlock]
    #: List of LayoutBlock objects describing the layout. This information is used
    #: in to_html() and similar methods to determine how to render the blocks.
    layout: list[LayoutBlock]

    is_commercial: bool = False

    #: If the post is a submission, this contains the username of the submitter.
    submitted_by: str | None = None

    @classmethod
    def from_post_dict(cls, data: dict) -> Self:
        """Turn post data from the Tumblr API into an NPFPost object."""

        assert "id" in data and "blog" in data

        # To avoid a cyclical dependency, we import Blog here instead of at the
        # top of the file.
        from .types import Blog

        return cls(
            id=data["id"],
            timestamp=data.get("timestamp", -1),
            blog=Blog.from_api(data["blog"]),
            content=[ContentBlock.from_dict(block) for block in data["content"]],
            layout=[LayoutBlock.from_dict(block) for block in data["layout"]],
            is_commercial=data.get("is_commercial", False),
        )

    @classmethod
    def from_trail_dict(cls, data: dict) -> Self:
        """Turn a post from a reblog trail into an NPFPost object."""

        assert "blog" in data or "broken_blog_name" in data

        # To avoid a cyclical dependency, we import Blog here instead of at the
        # top of the file.
        from .types import Blog

        if "broken_blog_name" in data:
            # Broken trail item
            _id = -1
            _blog = Blog.create_dummy(data.get("broken_blog_name", "unknown-user"))
        else:
            # Regular post
            _id = int(data.get("post", {}).get("id", -1))
            _blog = Blog.from_api(data["blog"])
        _timestamp = data.get("post", {}).get("timestamp", -1)

        if "is_submitted" in data and data["is_submitted"]:
            _submitted_by = data["post_author"]
        else:
            _submitted_by = None

        return cls(
            id=_id,
            timestamp=_timestamp,
            blog=_blog,
            content=[ContentBlock.from_dict(block) for block in data["content"]],
            layout=[LayoutBlock.from_dict(block) for block in data["layout"]],
            is_commercial=data.get("is_commercial", False),
            submitted_by=_submitted_by,
        )

    def to_html(self, truncate: bool = False) -> str:
        """
        Convert the post content into an HTML representation.

        :param truncate: Whether or not to add the "read more" block after the
            cutoff passed in the truncate_after variable of the rows layout.
            For posts without a truncate_after setting, this option does nothing.
        :returns: A string with a valid HTML representation of the post.
        """

        # Each ContentBlock subclass implements a .to_html() method which
        # converts the block content to HTML - *at single block level*.
        #
        # Layouts and tags that span *multiple blocks* are instead handled
        # in npf_to_html.

        out = npf_to_html(self.content, self.layout, truncate=truncate)

        if self.submitted_by:
            out += f'<div class="submitted-by">Submitted by <span class="submitter-username">{self.submitted_by}</span></div>'

        return out

    def to_markdown(self, truncate: bool = False) -> str:
        """
        Convert the post to Markdown.

        :param truncate: Whether or not to add the "read more" block after the
            cutoff passed in the truncate_after variable of the rows layout.
            For posts without a truncate_after setting, this option does nothing.
        :returns: A string containing a Markdown representation of the post.
        """

        # Markdown conversion works much the same as HTML conversion, but with
        # to_markdown methods. Most things are handled at the block level
        # except for ordered lists.

        out = npf_to_markdown(self.content, self.layout, truncate=truncate)

        if self.submitted_by:
            out += f"*(Submitted by {self.submitted_by})*"

        return out

    async def fetch_poll_results(self, api: "TumblrAPI", skip_cache: bool = False):
        """
        Fetch poll results for all polls in this post.

        :param api: TumblrAPI object to use for fetching.
        :param skip_cache: If True, ignores the cache.
        """
        for block in self.content:
            if isinstance(block, ContentBlockPoll):
                try:
                    await block.fetch_results(
                        api, self.blog.name, self.id, skip_cache=skip_cache
                    )
                except ValueError:
                    continue
