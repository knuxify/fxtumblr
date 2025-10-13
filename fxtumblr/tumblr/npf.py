# SPDX-License-Identifier: MIT
"""Parser for Tumblr's NPF ("Neue Post Format") format."""

import html
import itertools
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, Self

import emoji
from frozendict import frozendict

if TYPE_CHECKING:
    # Placed in TYPE_CHECKING due to circular import
    from .types import Blog

##
# Helper classes/functions
##


class UnknownContentBlockError(Exception):
    """Exception raised when the content block type is not known."""


def _closing_tag(tag: str) -> str:
    """Extract the tag name from a tag's content."""
    out = ""
    for i in tag:
        if i == " ":
            break
        out += i
    return out


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
    #: Width of the media.
    width: int
    #: Height of the media.
    height: int
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
            width=data["width"],
            height=data["height"],
            has_original_dimensions=data.get("has_original_dimensions", False),
        )


class MediaList(list):
    """List of Media objects. Provides a convenience method for finding media of a specific size."""

    @property
    def original_dimensions(self) -> tuple[int, int] | None:
        """
        Get the original dimensions of the media, if present.

        :returns: Tuple of width and height, or None if original dimensions could
            not be determined.
        """
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

    def to_html(self) -> str:
        """
        Convert the attribution data to a human-viewable HTML format.

        To be implemented by subclasses.

        :returns: The conversion result, as a string containing valid HTML.
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn ann attribution dict into an NPFContent object.

        To be implemented by subclasses.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        raise NotImplementedError


@dataclass
class AttributionPost(Attribution):
    """Attribution to a Tumblr post."""


##
# Content blocks
##


@dataclass
class ContentBlock:
    """Base class for NPF content blocks."""

    #: Content block type; defined by subclasses.
    type: ClassVar[str]

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        To be implemented by subclasses.

        :returns: The conversion result, as a string containing valid HTML.
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a content block dict into an NPFContent object.

        To be implemented by subclasses.

        :param data: Data to use for object creation.
        :returns: The resulting object.
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

    @property
    def html_tag(self) -> str:
        """HTML opening tag contents for this format."""
        if self.type == TextFormatType.bold:
            return "b"
        elif self.type == TextFormatType.italic:
            return "i"
        elif self.type == TextFormatType.strikethrough:
            return "strike"
        elif self.type == TextFormatType.small:
            return ("small",)
        elif self.type == TextFormatType.link:
            return (f"a href={self.url}",)
        elif self.type == TextFormatType.mention:
            return (f"a href={self.blog['url']}",)
        elif self.type == TextFormatType.color:
            return f'span style="color: {self.hex}"'
        return "span"

    @property
    def blog(self) -> frozendict:
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
            raise UnknownContentBlockError(
                f"Unknown formatting type {data['type']}"
            ) from e

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


@dataclass
class ContentBlockText(ContentBlock):
    """Text block representing a single paragraph of text."""

    type: ClassVar[str] = "text"

    #: Text inside the paragraph.
    text: str

    #: Subtype of the block.
    subtype: ContentTextSubtype | None = None

    #: Indentation level, for blocks with a list item subtype.
    #: Ignored for other subtypes.
    indent_level: int | None = None

    #: Formatting data.
    formatting: list[TextFormat] | None = None

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """

        if self.formatting:
            out = ""

            open_formats: deque[TextFormat] = deque()  # Stack of currently open formats
            temp_closed: deque[TextFormat] = (
                deque()
            )  # Temporary stack used to store closed formats
            # when fixing up HTML close tags
            format_starts = defaultdict(list)  # character: list of formats
            format_ends = defaultdict(list)  # character: list of formats

            for format in self.formatting:
                format_starts[format.start].append(format)
                format_ends[format.end].append(format)

            n_char = 0  # Currently parsed character *in the original text*;
            # used to determine format position
            for n_char in range(len(self.text) + 1):
                # Open formats that need starting
                for format in format_starts[n_char]:
                    out += f"<{format.html_tag}>"
                    open_formats.append(format)

                # Close formats that need ending
                if format_ends[n_char]:
                    # First, close tags until we close all the formats that end
                    # on this character
                    _ends = set(format_ends[n_char])
                    while not set(temp_closed).issuperset(_ends):
                        format = open_formats.pop()
                        temp_closed.append(format)
                        out += f"</{_closing_tag(format.html_tag)}>"

                    # Then, only reopen the ones we closed on the way
                    for f in _ends:
                        temp_closed.remove(f)

                    while temp_closed:
                        format = temp_closed.pop()
                        out += f"<{format.html_tag}>"
                        open_formats.append(format)

                    del _ends

                # Add HTML-escaped letter to output
                try:
                    out += html.escape(self.text[n_char])
                except IndexError:
                    # We parse one more character than the length of the text
                    # so that tags that span the entire text get correctly closed
                    # and we don't have to copy the tag closing logic after the loop.
                    # As such, if the index is too large, that means the loop has
                    # finished.
                    break

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
            elif self.subtype == ContentTextSubtype.ordered_list_item:
                out = "<li>" + out + "</li>"
            elif self.subtype == ContentTextSubtype.unordered_list_item:
                out = "<li>" + out + "</h2>"
            elif self.subtype == ContentTextSubtype.chat:
                out = '<p class="npf_chat">' + out + "</p>"
            elif self.subtype == ContentTextSubtype.quote:
                out = '<p class="npf_quote">' + out + "</p>"
            elif self.subtype == ContentTextSubtype.quirky:
                out = '<p class="npf_quirky">' + out + "</p>"

            # Apply emoji styling. (The use of self.text instead of out is deliberate;
            # it means that formatting tags are ignored.)
            elif len(self.text) > 0 and not self.text[0].isalnum():
                emoji_tuple = tuple(itertools.islice(emoji.analyze(self.text), 4))
                emoji_and_char_tuple = tuple(
                    itertools.islice(emoji.analyze(self.text, non_emoji=True), 4)
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

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a text content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type

        _indent_level = None
        if "subtype" in data:
            try:
                _subtype = ContentTextSubtype(data["subtype"])
            except ValueError as e:
                raise UnknownContentBlockError(
                    f"Unknown text block subtype {data['subtype']}"
                ) from e

            if _subtype in (
                ContentTextSubtype.ordered_list_item,
                ContentTextSubtype.unordered_list_item,
            ):
                _indent_level = data.get("indent_level", 0)

        else:
            _subtype = None

        if "formatting" in data:
            _formatting = [TextFormat.from_dict(i) for i in data["formatting"]]
            _formatting.sort(key=lambda f: f.start)
            _formatting.sort(key=lambda f: f.end, reverse=True)
        else:
            _formatting = None

        return cls(
            text=data["text"],
            subtype=_subtype,
            indent_level=_indent_level,
            formatting=_formatting,
        )


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

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        media_orig = self.media.get_hq()
        media_small = self.media.get_by_width(640)

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

        figure_tag = f'<figure class="{classes}"><img src="{media_small.url}"/>{badge_tag}</figure>'

        return figure_tag

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

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        if self.title:
            title = self.title
        elif self.display_url:
            title = self.display_url
        else:
            title = self.url

        html = '<div class="link-embed">'

        if self.poster:
            selected_size_poster = self.poster.get_by_width(540)
            html += f'<div class="link-embed-image-top"><img src="{selected_size_poster.url}" class="link-image"><span class="link-image-title">{title}</span></div>'
        else:
            html += f'<div class="link-embed-top"><span class="link-title">{title}</span></div>'

        html += '<div class="link-embed-bottom">'
        if self.description:
            html += f'<span class="link-description">{self.description}</span>'
        if self.site_name:
            html += f'<span class="link-sitename">{self.site_name}</span>'
        html += "</div></div>"

        return html

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


@dataclass
class ContentBlockVideo(ContentBlock):
    """Represents a video embed."""

    type: ClassVar[str] = "video"

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a video content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type
        return cls()


@dataclass
class ContentBlockAudio(ContentBlock):
    """Represents an audio embed."""

    type: ClassVar[str] = "audio"

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn an audio content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type
        return cls()


@dataclass
class ContentBlockPoll(ContentBlock):
    """Represents a poll embed."""

    type: ClassVar[str] = "poll"

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Turn a poll content block dict into an NPFContentText object.

        :param data: Data to use for object creation.
        :returns: The resulting object.
        """
        assert data["type"] == cls.type
        return cls()


@dataclass
class ContentBlockUnknown(ContentBlock):
    """Represents an unknown content block."""

    type: ClassVar[str] = "unknown"

    def to_html(self) -> str:
        """
        Convert the block data to HTML format.

        :returns: The conversion result, as a string containing valid HTML.
        """
        return


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


class LayoutBlock:
    """Base class for NPF layout blocks."""

    #: Layout block type; defined by subclasses.
    type: ClassVar[str]


##
# Post parsing
##


@dataclass
class NPFPost:
    """A single post in a trail."""

    id: int
    timestamp: int
    blog: "Blog"

    content: list[ContentBlock]
    layout: list[LayoutBlock]

    is_commercial: bool = False

    # TODO: Having this function support two different post types will bite us
    # in the ass. Fix this.
    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Turn a Tumblr API post response or post from reblog trail into an NPFPost object."""

        # To avoid a cyclical dependency, we import Blog here instead of at the
        # top of the file.
        from .types import Blog

        # This function accepts two types of post dicts, both largely
        # identical: regular post objects and trail items.
        # The only relevant difference is that the latter stores post
        # data in a "post" dict.

        # Trail post (https://www.tumblr.com/docs/npf#reblog-trail)
        if "id" not in data:
            if "id" not in data.get("post", {}):
                # Broken trail item
                _id = -1
                blog = Blog.create_dummy(data.get("broken_blog_name", "unknown-user"))
            else:
                _id = int(data["post"]["id"])
                blog = Blog.from_api(data["blog"])
            timestamp = data.get("post", {}).get("timestamp", -1)

        # Regular post
        else:
            _id = data["id"]
            timestamp = data.get("timestamp", -1)
            blog = Blog.from_api(data["blog"])

        return cls(
            id=_id,
            timestamp=timestamp,
            blog=blog,
            content=[],
            layout=[],
            is_commercial=data.get("is_commercial", False),
        )
