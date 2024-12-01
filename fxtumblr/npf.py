# NPF to HTML converter. Taken from pytumblr2 and extended for fxtumblr's needs:
# https://github.com/nostalgebraist/pytumblr2/blob/master/pytumblr2/format_conversion/npf2html.py


from typing import List, Optional, Tuple
from collections import defaultdict
from itertools import zip_longest
from copy import deepcopy
from markdownify import markdownify
import html
import nh3
import urllib
import datetime
import dateutil.parser
import itertools
import emoji
import re
from urllib.parse import urlparse

from .tumblr import tumblr, get_poll, get_avatar, DEFAULT_AVATAR

strip_tags = re.compile("<.*?>")


def _get_blogname_from_payload(post_payload):
    """retrieves payload --> broken_blog_name, or payload --> blog --> name"""
    if "broken_blog_name" in post_payload:
        return post_payload["broken_blog_name"]
    return post_payload["blog"]["name"]


def _get_avatar_from_payload(post_payload: dict) -> str:
    avatar = None
    if "blog" in post_payload:
        if "avatar" in post_payload["blog"]:
            avatar_media = NPFMediaList(post_payload["blog"]["avatar"])
            avatar = avatar_media._pick_one_size(32)["url"]
        else:
            avatar = get_avatar(post_payload["blog"]["name"])
    if not avatar:
        avatar = DEFAULT_AVATAR
    return avatar


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


class TumblrContentBlockBase:
    def to_html(self) -> str:
        raise NotImplementedError

    def to_markdown(self, placeholders: bool = False) -> str:
        raise NotImplementedError


class LegacyBlock(TumblrContentBlockBase):
    def __init__(self, body: str):
        self._body = body

    @property
    def body(self):
        return self._body

    def to_html(self):
        return self._body

    def to_markdown(self, placeholders: bool = False):
        return markdownify(self._body)


class NPFAttributionBase:
    def attribution_type(self):
        raise NotImplementedError

    def to_html(self) -> str:
        raise NotImplementedError

    def to_markdown(self, placeholders: bool = False) -> str:
        raise NotImplementedError


class NPFAttribution:
    def from_payload(payload: dict):
        if payload.get("type") == "post":
            return NPFPostAttribution.from_payload(payload)
        if payload.get("type") == "link":
            return NPFLinkAttribution.from_payload(payload)
        if payload.get("type") == "blog":
            return NPFBlogAttribution.from_payload(payload)
        if payload.get("type") == "app":
            return NPFAppAttribution.from_payload(payload)
        else:
            raise ValueError(payload.get("type"))


class NPFPostAttribution(NPFAttributionBase):
    def __init__(self, url: str, blog: dict):
        self._url = url
        self._blog = blog

    @staticmethod
    def attribution_type():
        return "post"

    @property
    def url(self):
        return self._url

    @property
    def blog(self):
        return self._blog

    def to_html(self):
        return f'<div class="attribution post-attribution"><a href="{self.url}">GIF by <b>{self.blog["name"]}</b></a></div>'

    @staticmethod
    def from_payload(payload: dict) -> "NPFPostAttribution":
        return NPFPostAttribution(
            url=payload.get("url"),
            blog=payload.get("blog"),
        )


class NPFLinkAttribution(NPFAttributionBase):
    def __init__(self, url: str):
        self._url = url

    @staticmethod
    def attribution_type():
        return "link"

    @property
    def url(self):
        return self._url

    def to_html(self):
        caret_tag = '<span class="attribution-go-icon"><svg xmlns="http://www.w3.org/2000/svg" height="14" width="14" role="presentation"><use href="#managed-icon__caret-fat"></use></svg></span>'

        return f'<div class="attribution image-attribution"><a href="{self.url}">{urlparse(self.url).netloc}</a>{caret_tag}</div>'

    @staticmethod
    def from_payload(payload: dict) -> "NPFLinkAttribution":
        return NPFLinkAttribution(
            url=payload.get("url"),
        )


class NPFBlogAttribution(NPFAttributionBase):
    def __init__(self, url: str, blog: dict):
        self._url = url
        self._blog = blog

    @staticmethod
    def attribution_type():
        return "blog"

    @property
    def url(self):
        return self._url

    @property
    def blog(self):
        return self._blog

    def to_html(self):
        return f'<div class="attribution blog-attribution"><a href="{self.url}">{self.blog["name"]}</a></div>'

    @staticmethod
    def from_payload(payload: dict) -> "NPFBlogAttribution":
        return NPFBlogAttribution(
            url=payload.get("url"),
            blog=payload.get("blog"),
        )


class NPFAppAttribution(NPFAttributionBase):
    def __init__(
        self,
        url: str,
        app_name: Optional[str] = None,
        display_text: Optional[str] = None,
    ):
        self._url = url
        self._app_name = app_name
        self._display_text = display_text

    @staticmethod
    def attribution_type():
        return "app"

    @property
    def url(self):
        return self._url

    @property
    def app_name(self):
        return self._app_name

    @property
    def display_text(self):
        return self._display_text

    def to_html(self):
        caret_tag = '<span class="attribution-go-icon"><svg xmlns="http://www.w3.org/2000/svg" height="14" width="14" role="presentation"><use href="#managed-icon__caret-fat"></use></svg></span>'

        if self.app_name and self.display_text and self.app_name != "Twitter":
            text = self.app_name + " | " + self.display_text
        elif self.display_text:
            text = self.display_text
        elif self.app_name:
            text = self.app_name
        else:
            text = urlparse(self.url).netloc

        return f'<div class="attribution app-attribution"><a href="{self.url}">{text}</a>{caret_tag}</div>'

    @staticmethod
    def from_payload(payload: dict) -> "NPFAppAttribution":
        return NPFAppAttribution(
            url=payload.get("url"),
            app_name=payload.get("app_name"),
            display_text=payload.get("display_text"),
        )


class NPFFormattingRange:
    def __init__(
        self,
        start: int,
        end: int,
        type: str,
        url: Optional[str] = None,
        blog: Optional[dict] = None,
        hex: Optional[str] = None,
    ):
        self.start = start
        self.end = end
        self.type = type

        self.url = url
        self.blog = blog
        self.hex = hex

    def to_html(self):
        result = {"start": self.start, "end": self.end}

        types_to_style_tags = {
            "bold": "b",
            "italic": "i",
            "small": "small",
            "strikethrough": "strike",
        }

        if self.type in types_to_style_tags:
            tag = types_to_style_tags[self.type]
            result["start_insert"] = f"<{tag}>"
            result["end_insert"] = f"</{tag}>"
        elif self.type == "underline":
            result["start_insert"] = f'<span style="text-decoration:underline">'
            result["end_insert"] = f"</span>"
        elif self.type == "link":
            result["start_insert"] = f'<a href="{self.url}">'
            result["end_insert"] = f"</a>"
        elif self.type == "mention":
            blog_url = self.blog.get("url")
            result["start_insert"] = f'<a class="tumblelog" href="{blog_url}">'
            result["end_insert"] = f"</a>"
        elif self.type == "color":
            result["start_insert"] = f'<span style="color:{self.hex}">'
            result["end_insert"] = f"</span>"
        else:
            raise ValueError(self.type)
        return result

    def to_markdown(self, placeholders=False):
        result = {"start": self.start, "end": self.end}

        types_to_style_tags = {
            "bold": "**",
            "italic": "**",
            "small": "_",
            "strikethrough": "~",
        }

        if self.type in types_to_style_tags:
            tag = types_to_style_tags[self.type]
            result["start_insert"] = tag
            result["end_insert"] = tag
        elif self.type == "link":
            result["start_insert"] = "["
            result["end_insert"] = "]"
        elif self.type == "mention":
            if placeholders:
                result["start_insert"] = ""
                result["end_insert"] = ""
            else:
                blog_url = self.blog.get("url")
                result["start_insert"] = "["
                result["end_insert"] = f"]({blog_url})"
        else:
            result["start_insert"] = "*"
            result["end_insert"] = "*"
        return result


class NPFSubtype:
    def __init__(self, subtype: str):
        self.subtype = subtype

    def format_html(self, text: str):
        text_or_break = text if len(text) > 0 else "<br>"

        if self.subtype == "heading1":
            ret = f"<h1>{text_or_break}</h1>"
        elif self.subtype == "heading2":
            ret = f"<h2>{text_or_break}</h2>"
        elif self.subtype == "ordered-list-item":
            ret = f"<li>{text}</li>"
        elif self.subtype == "unordered-list-item":
            ret = f"<li>{text}</li>"
        elif self.subtype == "indented":
            ret = text
        # These match the standard classes used in Tumblr's CSS:
        elif self.subtype == "chat":
            ret = f'<span class="npf_chat">{text_or_break}</span>'
        elif self.subtype == "quote":
            ret = f'<span class="npf_quote">{text_or_break}</span>'
        elif self.subtype == "quirky":
            ret = f'<span class="npf_quirky">{text_or_break}</span>'
        elif len(text) > 0 and not text[0].isalnum():
            # We get 4 items here since we need to check if there aren't more than 3
            emoji_tuple = tuple(itertools.islice(emoji.analyze(text), 4))
            emoji_and_char_tuple = tuple(
                itertools.islice(
                    emoji.analyze(re.sub(strip_tags, "", text), non_emoji=True), 4
                )
            )
            if len(emoji_tuple) <= 3 and [e.chars for e in emoji_tuple] == [
                e.chars for e in emoji_and_char_tuple
            ]:
                ret = f'<p class="emoji-large">{text}</p>'
            else:
                ret = f"<p>{text_or_break}</p>"
        elif len(text) == 0:
            return ""
        else:
            ret = f"<p>{text_or_break}</p>"

        if self.subtype not in ("ordered-list-item", "unordered-list-item", "indented"):
            ret = '<div class="text-block">' + ret + "</div>"

        return ret

    def format_markdown(self, text: str):
        if not text:
            return ""
        if self.subtype == "heading1":
            return f"\n# {text}"
        elif self.subtype == "heading2":
            return f"\n## {text}"
        elif self.subtype == "ordered-list-item":
            return f"\n* {text}"
        elif self.subtype == "unordered-list-item":
            return f"\n* {text}"
        # These match the standard classes used in Tumblr's CSS:
        elif self.subtype in ("chat", "quote", "quirky"):
            return f"\n*{text}*"
        elif len(text) == 0:
            return ""
        else:
            return f"\n{text}"


class NPFBlock(TumblrContentBlockBase):
    def from_payload(payload: dict) -> "NPFBlock":
        if payload.get("type") == "text":
            return NPFTextBlock.from_payload(payload)
        elif payload.get("type") == "image":
            return NPFImageBlock.from_payload(payload)
        elif payload.get("type") == "video":
            # Handle some known bad embeds by turning them into links:
            if payload.get("provider") == "twitch_live":
                return NPFLinkBlock.from_payload(
                    {
                        "url": payload["url"],
                        "sitename": "twitch.tv",
                        "title": payload["url"].replace("https://www.twitch.tv/", "")
                        + " on Twitch",
                        "description": "Twitch is the world's leading video platform and community for gamers.",
                    }
                )
            elif payload.get("provider") == "instagram":
                return NPFLinkBlock.from_payload(
                    {
                        "url": payload["url"],
                        "sitename": "Instagram",
                        "title": f'Video by {payload["attribution"]["display_text"]} on Instagram',
                        "description": f"See Instagram photos and videos from @{payload['attribution']['display_text']}",
                    }
                )
            return NPFVideoBlock.from_payload(payload)
        elif payload.get("type") == "audio":
            return NPFAudioBlock.from_payload(payload)
        elif payload.get("type") == "link":
            return NPFLinkBlock.from_payload(payload)
        elif payload.get("type") == "poll":
            return NPFPollBlock.from_payload(payload)
        else:
            raise ValueError(payload.get("type"))

    @property
    def attribution(self):
        return None


class NPFTextBlock(NPFBlock):
    def __init__(
        self,
        text: str,
        subtype: Optional[NPFSubtype] = None,
        indent_level: Optional[int] = None,
        formatting: List[NPFFormattingRange] = None,
    ):
        self.text = text
        self.subtype = NPFSubtype("no_subtype") if subtype is None else subtype
        self.indent_level = 0 if indent_level is None else indent_level
        self.formatting = [] if formatting is None else formatting

    @property
    def subtype_name(self):
        return self.subtype.subtype

    def apply_formatting(self, markdown: bool = False, placeholders: bool = False):
        if markdown:
            insertions = [
                formatting.to_markdown(placeholders=placeholders)
                for formatting in self.formatting
            ]
            text = self.text
        else:
            insertions = [formatting.to_html() for formatting in self.formatting]
            # For HTML formatting, we must first escape HTML characters in the text,
            # then apply formatting, then return the result. We can't escape the result
            # or the tags we add will be escaped as well; we can't just escape the input
            # text without changing the length of it, and causing formatting to drift off.
            # So, first, modify the insertions to accomodate for the offset.

            text = ""
            offset = 0
            n = 0
            for char in self.text:
                esc = html.escape(char)
                if esc != char:
                    new_offset = len(esc) - 1
                    for insertion in insertions:
                        if insertion["start"] > (n + offset):
                            insertion["start"] += new_offset
                        if insertion["end"] > (n + offset):
                            insertion["end"] += new_offset
                    offset += new_offset
                text += esc
                n += 1

        insert_ix_to_inserted_text = defaultdict(list)
        for insertion in insertions:
            insert_ix_to_inserted_text[insertion["start"]].append(
                insertion["start_insert"]
            )
            insert_ix_to_inserted_text[insertion["end"]].append(insertion["end_insert"])

        split_ixs = {0, len(text)}
        split_ixs.update(insert_ix_to_inserted_text.keys())
        split_ixs = sorted(split_ixs)

        accum = []

        for ix1, ix2 in zip_longest(split_ixs, split_ixs[1:], fillvalue=split_ixs[-1]):
            accum.extend(insert_ix_to_inserted_text[ix1])
            accum.append(text[ix1:ix2])

        return "".join(accum)

    def to_html(self):
        formatted = self.apply_formatting(markdown=False)

        if self.subtype is not None:
            formatted = self.subtype.format_html(formatted)

        return formatted

    def to_markdown(self, placeholders: bool = False):
        formatted = self.apply_formatting(markdown=True, placeholders=placeholders)

        if self.subtype is not None:
            formatted = self.subtype.format_markdown(formatted)

        return formatted

    @staticmethod
    def from_payload(payload: dict) -> "NPFTextBlock":
        return NPFTextBlock(
            text=payload["text"],
            subtype=NPFSubtype(subtype=payload.get("subtype", "no_subtype")),
            indent_level=payload.get("indent_level"),
            formatting=[
                NPFFormattingRange(**entry) for entry in payload.get("formatting", [])
            ],
        )


class NPFNonTextBlockMixin:
    @property
    def subtype_name(self):
        return "no_subtype"

    @property
    def indent_level(self):
        return 0


class NPFMediaList:
    def __init__(self, media: List[dict]):
        self._media = media

    @property
    def media(self):
        return self._media

    @property
    def original_dimensions(self) -> Optional[Tuple[int, int]]:
        for entry in self.media:
            if entry.get("has_original_dimensions"):
                return (entry["width"], entry["height"])

    def _pick_one_size(self, target_width: int = 640) -> dict:
        by_width_descending = sorted(
            self.media, key=lambda entry: entry["width"], reverse=True
        )
        for entry in by_width_descending:
            if entry["width"] <= target_width:
                return entry
        return by_width_descending[-1]


class NPFMediaBlock(NPFBlock, NPFNonTextBlockMixin):
    def __init__(
        self,
        media: Optional[List[dict]] = [],
        alt_text: Optional[str] = None,
        embed_html: Optional[str] = None,
        poster: Optional[dict] = [],
        data: Optional[dict] = {},
        attribution: Optional[dict] = {},
    ):
        self._media = NPFMediaList(media)
        self._alt_text = alt_text
        self._embed_html = embed_html
        self._poster = NPFMediaList(poster) if poster else None
        self._data = data
        self._attribution = (
            NPFAttribution.from_payload(attribution) if attribution else None
        )

    @property
    def media(self):
        return self._media

    @property
    def alt_text(self):
        return self._alt_text

    @property
    def poster(self):
        return self._poster

    @property
    def embed_html(self) -> Optional[str]:
        return self._embed_html

    @property
    def data(self):
        return self._data

    @property
    def attribution(self):
        return self._attribution


class NPFImageBlock(NPFMediaBlock):
    @staticmethod
    def from_payload(payload: dict) -> "NPFImageBlock":
        return NPFImageBlock(
            media=payload["media"],
            alt_text=payload.get("alt_text"),
            data={"caption": payload.get("caption")},
            attribution=payload.get("attribution"),
        )

    def to_html(self, target_width: int = 640) -> str:
        selected_size = self.media._pick_one_size(target_width)
        width = selected_size["width"]

        original_dimensions_attrs_str = ""
        if self.media.original_dimensions is not None:
            orig_w, orig_h = self.media.original_dimensions
            original_dimensions_attrs_str = (
                f' data-orig-height="{orig_h}" data-orig-width="{orig_w}"'
            )
            width = orig_w

        img_tag = (
            f"<img src=\"{selected_size['url']}\"{original_dimensions_attrs_str}/>"
        )

        alt_tag = ""
        if "gif" in selected_size["url"]:
            alt_tag = '<span class="tmblr-alt-text-helper">GIF</span>'
        elif self.alt_text:
            alt_tag = '<span class="tmblr-alt-text-helper">ALT</span>'

        figure_tag = f'<figure class="tmblr-full{ " orig-size" if width < 300 else "" }{ " gif" if "gif" in selected_size["url"] else ""}"{original_dimensions_attrs_str}>{img_tag}{alt_tag}</figure>'

        return figure_tag

    def to_markdown(self, target_width: int = 640, placeholders: bool = False) -> str:
        if placeholders:
            return "\n(image)"

        selected_size = self.media._pick_one_size(target_width)

        return f"\n![Image]({selected_size['url']})"


class NPFVideoBlock(NPFMediaBlock):
    @staticmethod
    def from_payload(payload: dict) -> "NPFVideoBlock":
        # Sometimes videos will not have a poster, but it's still possible to
        # get the thumbnail by modifying the URL.
        poster = []
        if "poster" in payload:
            poster = payload["poster"]
        elif "media" in payload and payload["media"]:
            media = NPFMediaList([payload["media"]])
            if media.media:
                original_dimensions = media.original_dimensions
                if not original_dimensions:
                    original_dimensions = (640, 640)
                selected_size = media._pick_one_size(
                    target_width=original_dimensions[0]
                )
                if selected_size and "media.tumblr.com" in selected_size["url"]:
                    poster_url = (
                        urllib.parse.urlparse(selected_size["url"])
                        ._replace(netloc="64.media.tumblr.com")
                        .geturl()
                        .replace(".mp4", "_frame1.jpg")
                        .replace("_720_frame1", "_frame1")
                    )
                    poster = [
                        {
                            "url": poster_url,
                            "type": "image/jpg",
                            "width": selected_size["width"],
                            "height": selected_size["height"],
                        }
                    ]

        return NPFVideoBlock(
            media=[payload["media"]] if "media" in payload else [],
            alt_text=payload.get("alt_text"),
            poster=poster,
            embed_html=payload["embed_html"] if "embed_html" in payload else "",
            attribution=payload.get("attribution"),
        )

    def to_standard_html(self, target_width: int = 640) -> str:
        # this is unused, but left in case it's ever useful to anyone
        if self.embed_html:
            return self.embed_html

        selected_size_poster = None
        if self.poster:
            selected_size_poster = self.poster._pick_one_size(target_width)

        original_dimensions_attrs_str = ""
        if self.media.original_dimensions is not None:
            orig_w, orig_h = self.media.original_dimensions
            original_dimensions_attrs_str = (
                f' data-orig-height="{orig_h}" data-orig-width="{orig_w}"'
            )

        video_tag = f"<video "
        if selected_size_poster:
            video_tag += f"poster=\"{selected_size_poster['url']}\""
        video_tag += f'controls="controls"{original_dimensions_attrs_str}><source src="{self.media.media[0]["url"]}" type="video/mp4"></video>'

        figure_tag = f'<figure class="tmblr-full"{original_dimensions_attrs_str}>{video_tag}</figure>'

        return figure_tag

    def to_html(self, target_width: int = 640) -> str:
        selected_size = None
        if self.poster:
            selected_size = self.poster._pick_one_size(target_width)

        if selected_size:
            img_tag = f"<img class=\"video-poster\" src=\"{selected_size['url']}\"/>"
        else:
            img_tag = '<div class="video-poster video-poster-dummy"></div>'

        play_button_tag = '<span class="tmblr-play-button-helper"><svg xmlns="http://www.w3.org/2000/svg" height="32" width="32" role="presentation" style="--icon-color-primary: RGB(255, 255, 255);"><use href="#managed-icon__play-cropped"></use></svg></span>'

        alt_tag = ""
        if self.alt_text:
            alt_tag = '<span class="tmblr-alt-text-helper">ALT</span>'

        figure_tag = f'<figure class="tmblr-full video-block">{img_tag}{play_button_tag}{alt_tag}</figure>'

        return figure_tag

    def to_markdown(self, target_width: int = 640, placeholders: bool = False) -> str:
        if self.embed_html:
            if placeholders:
                return "\n(video embed)"
            return self.embed_html
        if placeholders:
            return "\n(video)"

        if self.poster:
            selected_size_poster = self.poster._pick_one_size(target_width)
            return f"\n![Video thumbnail]({selected_size_poster['url']})"
        return "\n(video)"


class NPFAudioBlock(NPFMediaBlock):
    @staticmethod
    def from_payload(payload: dict) -> "NPFAudioBlock":
        return NPFAudioBlock(
            media=[payload["media"]] if "media" in payload else [],
            alt_text=payload.get("alt_text"),
            poster=payload["poster"] if "poster" in payload else None,
            embed_html=payload["embed_html"] if "embed_html" in payload else "",
            data={
                "title": payload.get("title", ""),
                "artist": payload.get("artist", ""),
                "album": payload.get("album", ""),
                "provider": payload.get("provider"),
            },
            attribution=payload.get("attribution"),
        )

    def to_standard_html(self) -> str:
        # this is unused, but left in case it's ever useful to anyone
        if self.embed_html:
            return self.embed_html

        audio_tag = f"<audio src=\"{self.media.media[0]['url']}\" controls=\"controls\" muted=\"muted\"/>"

        figure_tag = f'<figure class="tmblr-full">{audio_tag}</figure>'

        return figure_tag

    def to_html(self) -> str:
        # This returns a (nonfunctional) official client-like view of an
        # audio track.
        selected_size_poster = None
        if self.poster:
            selected_size_poster = self.poster._pick_one_size(85)
        poster_url = ""
        if selected_size_poster and "url" in selected_size_poster:
            poster_url = selected_size_poster["url"]

        provider = self.data.get("provider")

        html = f"""
                <div class="audio-player{' audio-' + provider if provider else ''}">
                    <div class="play-button">
                        <svg xmlns="http://www.w3.org/2000/svg" height="24" width="24" role="presentation" style="--icon-color-primary: RGB(var(--white));"><use href="#managed-icon__{provider if provider in ("spotify", "soundcloud") else "play-cropped"}"></use></svg>
                    </div>
                    <div class="audio-info">
                        <div class="title">{self.title}</div>
                        <div class="artist">{self.artist}</div>
                        <div class="album">{self.album}</div>
                    </div>
        """
        if poster_url:
            html += f"""
                    <div class="audio-image">
                        <img src="{poster_url}">
                    </div>
            """
        html += """
                </div>
        """

        return html

    def to_markdown(self, placeholders: bool = False) -> str:
        if self.embed_html:
            if placeholders:
                return "\n(audio embed)"
            return self.embed_html
        if placeholders:
            return "\n(audio)"

        # todo: return poster
        return "\n(audio)"

    @property
    def title(self):
        return self.data["title"]

    @property
    def artist(self):
        return self.data["artist"]

    @property
    def album(self):
        return self.data["album"]


class NPFLinkBlock(NPFBlock, NPFNonTextBlockMixin):
    @staticmethod
    def from_payload(payload: dict) -> "NPFTextBlock":
        return NPFLinkBlock(
            url=payload["url"],
            title=payload.get("title"),
            description=payload.get("description"),
            author=payload.get("author"),
            site_name=payload.get("site_name"),
            display_url=payload.get("display_url"),
            poster=payload.get("poster"),
        )

    def __init__(
        self,
        url: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        author: Optional[str] = None,
        site_name: Optional[str] = None,
        display_url: Optional[str] = None,
        poster: Optional[dict] = [],
    ):
        self._url = url
        self._title = title
        self._description = description
        self._author = author
        self._site_name = site_name
        self._display_url = display_url
        self._poster = NPFMediaList(poster) if poster else None

    @property
    def url(self):
        return self._url

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def author(self):
        return self._author

    @property
    def site_name(self):
        return self._site_name

    @property
    def display_url(self):
        return self._display_url

    @property
    def poster(self):
        return self._poster

    def to_html(self) -> str:
        title = ""
        if self.title:
            title = self.title
        elif self.display_url:
            title = self.display_url
        else:
            title = self.url

        html = '<div class="link-embed">'

        if self.poster:
            selected_size_poster = self.poster._pick_one_size(540)
            html += f'<div class="link-embed-image-top"><img src="{selected_size_poster["url"]}" class="link-image"><span class="link-image-title">{title}</span></div>'
        else:
            html += f'<div class="link-embed-top"><span class="link-title">{title}</span></div>'

        html += '<div class="link-embed-bottom">'
        if self.description:
            html += f'<span class="link-description">{self.description}</span>'
        if self.site_name:
            html += f'<span class="link-sitename">{self.site_name}</span>'
        html += "</div></div>"

        return html

    def to_markdown(self, placeholders: bool = False) -> str:
        if self.title:
            return f"[{self.title}]({self.url})"
        elif self.display_url:
            return f"[{self.display_url}]({self.url})"
        return f"[{self.url}]({self.url})"


class NPFPollBlock(NPFBlock, NPFNonTextBlockMixin):
    @staticmethod
    def from_payload(payload: dict) -> "NPFPollBlock":
        data = {}
        # Tumblr's poll API requires a blog name and ID to be passed,
        # which we can't access at the block level, so this is fetched
        # elsewhere (look up _fxtumblr_poll_results for the relevant code)
        # and copied into the payload for parsing.
        # Also, the poll data is missing like half of the actually useful
        # information needed for a poll; so, we cache it here instead of
        # when we get it. It's not nice, but it works to cache things,
        # so oh well.
        if "_fxtumblr_poll_results" in payload:
            data = payload["_fxtumblr_poll_results"]

        return NPFPollBlock(
            question=payload["question"],
            answers=payload["answers"],
            created_at=payload["created_at"],
            settings=payload["settings"],
            data=data,
        )

    def __init__(
        self,
        question: str,
        answers: dict,
        created_at: str,
        settings: dict,
        data: dict,
    ):
        self._question = question
        self._answers = answers
        self._created_at = created_at
        self._settings = settings
        self._data = data

    @property
    def question(self):
        return self._question

    @property
    def answers(self):
        return self._answers

    @property
    def created_at(self):
        return self._created_at

    @property
    def settings(self):
        return self._settings

    @property
    def data(self):
        return self._data

    def to_html(self) -> str:
        total_votes = -1
        vote_str = ""
        if self.data:
            all_votes = [votes for votes in self.data["results"].values()]
            total_votes = sum(all_votes)
            most_votes = max(all_votes)
            vote_str = f'{total_votes:,} vote{"s" if total_votes != 1 else ""}'

        created_at = dateutil.parser.parse(self.created_at)
        expire_delta = datetime.timedelta(seconds=self.settings["expire_after"])
        end_time = created_at + expire_delta
        now = datetime.datetime.now(datetime.timezone.utc)
        is_over = False
        if end_time > now:
            time_remaining = end_time - now

            # https://stackoverflow.com/questions/14190045/how-do-i-convert-datetime-timedelta-to-minutes-hours-in-python
            days, seconds = time_remaining.days, time_remaining.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60

            if days > 0:
                time_str = f"{(vote_str + ' • ') if vote_str else ''}Remaining time: {days} days {hours} hours"
            else:
                time_str = f"{(vote_str + ' • ') if vote_str else ''}Remaining time: {hours} hours {minutes} minutes"
        else:
            time_str = "Final result"
            is_over = True

        html = f'<div class="poll-block{" poll-over" if is_over else ""}"><span class="poll-question">{self.question}</span>'

        if self.data and is_over:
            time_str += f" from {vote_str}"

            for answer in self.answers:
                answer_count = self.data["results"][answer["client_id"]]
                if answer_count == most_votes:
                    color = "var(--accent), .4"
                else:
                    color = "var(--black), .1"
                if total_votes:
                    answer_percentage = (answer_count / total_votes) * 100
                    answer_percentage = (
                        "{:.2f}".format(answer_percentage)
                        if not str(answer_percentage).endswith(".0")
                        else int(answer_percentage)
                    )
                else:
                    answer_percentage = 0
                html += f'<div class="poll-answer{" poll-answer-win" if answer_count == most_votes else ""}"><div class="poll-answer-filler" style="width: {answer_percentage}%;"></div><span class="poll-answer-text">{answer["answer_text"]}</span><span class="poll-answer-percentage">{answer_percentage}%</span></div>'
        else:
            for answer in self.answers:
                html += f'<div class="poll-answer">{answer["answer_text"]}</div>'

        html += f'<span class="poll-meta">{time_str}</span></div>'

        return html

    def to_markdown(self, placeholders: bool = False) -> str:
        return f"{self.question}\n *" + "\n *".join(
            answer["answer_text"] for answer in self.answers
        )


class NPFReadMoreBlock(NPFBlock, NPFNonTextBlockMixin):
    # Dummy "Read more" block for truncated threads
    def __init__(self):
        pass

    def to_html(self) -> str:
        return '<div class="read-more">Keep reading</div>'

    def to_markdown(self, placeholders: bool = False) -> str:
        return "\n(keep reading)"


class NPFSubmissionBlock(NPFBlock, NPFNonTextBlockMixin):
    # Dummy "Submitted by" block for submitted posts
    def __init__(self, submitted_by):
        self.submitted_by = submitted_by

    def to_html(self) -> str:
        return f'<div class="submitted-by">Submitted by <span class="submitter-username">{self.submitted_by}</span></div>'

    def to_markdown(self, placeholders: bool = False) -> str:
        # Handled in embed.py
        # f"\n\n(Submitted by {self.submitted_by})"
        return ""


class NPFLayout:
    @property
    def layout_type(self):
        return self._layout_type

    def from_payload(payload: dict) -> "NPFLayout":
        if payload.get("type") == "rows":
            return NPFLayoutRows.from_payload(payload)
        elif payload.get("type") == "ask":
            return NPFLayoutAsk.from_payload(payload)
        else:
            raise ValueError(payload.get("type"))


class NPFLayoutMode:
    def __init__(self, mode_type: str):
        self._mode_type = mode_type

    @property
    def mode_type(self):
        return self._mode_type

    @staticmethod
    def from_payload(payload: dict) -> "NPFLayoutMode":
        return NPFLayoutMode(mode_type=payload["type"])


class NPFLayoutRows(NPFLayout):
    def __init__(
        self,
        rows: List[int],
        truncate_after: Optional[int] = None,
    ):
        self._rows = rows
        self._truncate_after = truncate_after
        self._layout_type = "rows"

    @property
    def rows(self):
        return self._rows

    @property
    def truncate_after(self):
        return self._truncate_after

    @staticmethod
    def from_payload(payload: dict) -> "NPFLayoutRows":
        rows = [entry["blocks"] for entry in payload["display"]]
        return NPFLayoutRows(rows=rows, truncate_after=payload.get("truncate_after"))


class NPFLayoutAsk(NPFLayout):
    def __init__(
        self,
        blocks: List[int],
        attribution: Optional[dict] = None,
    ):
        self._blocks = blocks
        self._attribution = attribution
        self._layout_type = "ask"

    @property
    def blocks(self):
        return self._blocks

    @property
    def attribution(self):
        return self._attribution

    @property
    def asking_name(self):
        if self.attribution is None:
            return "Anonymous"
        return self.attribution["url"].partition(".tumblr.com")[0].partition("//")[2]

    @staticmethod
    def from_payload(payload: dict) -> "NPFLayoutAsk":
        return NPFLayoutAsk(
            blocks=payload["blocks"], attribution=payload.get("attribution")
        )


class NPFBlockAnnotated(NPFBlock):
    def __init__(
        self,
        base_block: NPFBlock,
        is_ask_block: bool = False,
        ask_layout: Optional[NPFLayoutAsk] = None,
    ):
        self.base_block = base_block

        self.prefix = ""
        self.suffix = ""
        self.is_ask_block = is_ask_block
        self.ask_layout = ask_layout

    def reset_annotations(self):
        new = NPFBlockAnnotated(base_block=self.base_block)
        for attr, value in new.__dict__.items():
            setattr(self, attr, value)

    def as_ask_block(self, ask_layout: NPFLayoutAsk) -> "NPFBlockAnnotated":
        new = deepcopy(self)
        new.is_ask_block = True
        new.ask_layout = ask_layout
        return new

    @property
    def asking_name(self):
        if not self.is_ask_block:
            return None
        if self.ask_layout is None:
            return None
        return self.ask_layout.asking_name

    def to_html(self) -> str:
        inside = self.base_block.to_html()
        return self.prefix + inside + self.suffix

    def to_markdown(self, placeholders: bool = False) -> str:
        inside = self.base_block.to_markdown(placeholders=placeholders)
        return self.prefix + inside + self.suffix


class TumblrContentBase:
    def __init__(self, content: List[TumblrContentBlockBase]):
        self.content = content

    def to_html(self) -> str:
        raise NotImplementedError

    def to_markdown(self, placeholders: bool = False) -> str:
        raise NotImplementedError


class NPFContent(TumblrContentBase):
    def __init__(
        self,
        blocks: List[NPFBlock],
        layout: List[NPFLayout],
        blog_name: str,
        avatar: str,
        id: Optional[int] = None,
        genesis_post_id: Optional[int] = None,
        post_url: Optional[str] = None,
        unroll: bool = False,
    ):
        self.raw_blocks = [
            block if isinstance(block, NPFBlockAnnotated) else NPFBlockAnnotated(block)
            for block in blocks
        ]
        self.layout = layout
        self.blog_name = blog_name
        self.avatar = avatar
        self.id = id
        self.genesis_post_id = genesis_post_id
        self._post_url = post_url
        self.unroll = unroll
        self._truncated = False
        self.is_submission = False
        self.submitted_by = None
        if not unroll:
            for layout_entry in self.layout:
                if (
                    isinstance(layout_entry, NPFLayoutRows)
                    and layout_entry.truncate_after is not None
                ):
                    self._truncated = True
                    break

        self.blocks = self._make_blocks()

    @property
    def post_url(self) -> str:
        if self._post_url is None and self.id is not None:
            # N.B. this doesn't have the "slug", while the API's post_url does
            return f"https://{self.blog_name}.tumblr.com/post/{self.id}/"
        return self._post_url

    @property
    def legacy_prefix_link(self):
        return f'<p><a class="tumblr_blog" href="{self.post_url}">{self.blog_name}</a>:</p>'

    def _make_blocks(self) -> List[NPFBlockAnnotated]:
        truncated = False
        if len(self.layout) == 0:
            ret = self.raw_blocks.copy()
        else:
            ordered_block_ixs = []
            ask_ixs = set()
            ask_ixs_to_layouts = {}
            for layout_entry in self.layout:
                if layout_entry.layout_type == "rows":
                    for row_ixs in layout_entry.rows:
                        if (
                            not self.unroll
                            and layout_entry.truncate_after is not None
                            and (layout_entry.truncate_after + 1) in row_ixs
                        ):
                            truncated = True

                        # note: deduplication here is needed b/c of april 2021 tumblr npf ask bug
                        if not self.unroll:
                            deduped_ixs = [
                                ix
                                for ix in row_ixs
                                if ix not in ordered_block_ixs
                                and (
                                    layout_entry.truncate_after is None
                                    or ix <= layout_entry.truncate_after
                                )
                            ]
                        else:
                            deduped_ixs = [
                                ix for ix in row_ixs if ix not in ordered_block_ixs
                            ]
                        ordered_block_ixs.extend(deduped_ixs)
                        if truncated:
                            break
                elif layout_entry.layout_type == "ask":
                    # note: deduplication here is needed b/c of april 2021 tumblr npf ask bug
                    deduped_ixs = [
                        ix for ix in layout_entry.blocks if ix not in ordered_block_ixs
                    ]
                    ordered_block_ixs.extend(deduped_ixs)
                    ask_ixs.update(layout_entry.blocks)
                    ask_ixs_to_layouts.update(
                        {ix: layout_entry for ix in layout_entry.blocks}
                    )

            if all([layout_entry.layout_type == "ask" for layout_entry in self.layout]):
                extras = [ix for ix in range(len(self.raw_blocks)) if ix not in ask_ixs]
                ordered_block_ixs.extend(extras)
            ret = [
                (
                    self.raw_blocks[ix].as_ask_block(ask_layout=ask_ixs_to_layouts[ix])
                    if ix in ask_ixs
                    else self.raw_blocks[ix]
                )
                for ix in ordered_block_ixs
            ]

        if self.is_submission:
            ret.append(
                NPFBlockAnnotated(base_block=NPFSubmissionBlock(self.submitted_by))
            )

        if truncated:
            ret.append(NPFBlockAnnotated(base_block=NPFReadMoreBlock()))

        return ret

    @property
    def ask_blocks(self) -> List[NPFBlockAnnotated]:
        return [bl for bl in self.blocks if bl.is_ask_block]

    @property
    def ask_layout(self) -> Optional[NPFLayoutAsk]:
        ask_layouts = [lay for lay in self.layout if lay.layout_type == "ask"]
        if len(ask_layouts) > 0:
            return ask_layouts[0]

    @property
    def has_ask(self) -> bool:
        return len(self.ask_blocks) > 0

    @property
    def truncated(self) -> bool:
        return self._truncated

    @staticmethod
    def from_payload(
        payload: dict, raise_on_unimplemented: bool = False, unroll: bool = False
    ) -> "NPFContent":
        blog_name = _get_blogname_from_payload(payload)

        avatar = _get_avatar_from_payload(payload)

        if "id" in payload:
            id = payload["id"]
        elif "post" in payload:
            # trail format
            id = payload["post"]["id"]
        else:
            # broken trail item format
            id = None
        id = int(id) if id is not None else None

        genesis_post_id = payload.get("genesis_post_id")
        genesis_post_id = int(genesis_post_id) if genesis_post_id is not None else None

        blocks = []
        for bl in payload["content"]:
            if bl.get("type") == "poll" and id:
                # FIXME: Tumblr's poll API sucks and is missing half of the useful information.
                # So, we have to provide the entire block payload to copy the poll data from.
                bl["_fxtumblr_poll_results"] = get_poll(
                    blog_name, str(id), bl["client_id"], bl
                )
            try:
                blocks.append(NPFBlock.from_payload(bl))
            except ValueError as e:
                if raise_on_unimplemented:
                    raise e
                # generic default/fake filler block
                blocks.append(
                    NPFTextBlock("(Unimplemented block; click to see the full post)")
                )

        layout = []
        for lay in payload["layout"]:
            try:
                layout.append(NPFLayout.from_payload(lay))
            except ValueError as e:
                if raise_on_unimplemented:
                    raise e

        post_url = payload.get("post_url")
        return NPFContent(
            blocks=blocks,
            layout=layout,
            blog_name=blog_name,
            avatar=avatar,
            id=id,
            genesis_post_id=genesis_post_id,
            post_url=post_url,
            unroll=unroll,
        )

    def _reset_annotations(self):
        for bl in self.blocks:
            bl.reset_annotations()
        self.blocks = self._make_blocks()

    def _assign_html_indents(self, wrap_blocks=False):
        # This is what the block is wrapped in. The actual contents of the
        # block itself are wrapped in the <p>, <li> elements as needed.
        subtype_wrappers = {
            "indented": "blockquote",
            "ordered-list-item": "ol",
            "unordered-list-item": "ul",
        }

        subtype_wrapper_classes = {}
        if wrap_blocks:
            subtype_wrapper_classes = {
                "indented": "text-block text-indented",
                "ordered-list-item": "text-list",
                "unordered-list-item": "text-list",
            }

        indent_level = 0
        type_stack = []
        closing_tags = []

        n = 0
        for block in self.blocks:
            if n != 0:
                previous_subtype = self.blocks[n - 1].base_block.subtype_name
            else:
                previous_subtype = "no_subtype"
            subtype = block.base_block.subtype_name

            indent_delta = block.base_block.indent_level - indent_level
            indent_delta_abs = abs(indent_delta)

            if subtype != previous_subtype and previous_subtype in subtype_wrappers:
                # If the subtype has changed, dump the last closing tag into the prefix
                block.prefix = closing_tags.pop() + block.prefix
                type_stack.pop()

            if subtype in subtype_wrappers:
                if subtype != previous_subtype:
                    # If the indent stays the same, and the subtype is changed,
                    # then we just need to add the prefix for the new tag (we
                    # added the closing tag for the previous type already).
                    if subtype in subtype_wrapper_classes:
                        block.prefix = (
                            block.prefix
                            + f'<{subtype_wrappers[subtype]} class="{subtype_wrapper_classes[subtype]}">'
                        )
                    else:
                        block.prefix = block.prefix + f"<{subtype_wrappers[subtype]}>"
                    closing_tags.append(f"</{subtype_wrappers[subtype]}>")
                    type_stack.append(subtype)

                # TODO: These next cases are... kinda broken. Indentation levels are
                # currently completely ignored by Tumblr and it is **impossible**
                # to make a post that's as advanced as in the docs (and even if it
                # was, nobody in their right mind would do it, except to piss me off).
                # See https://github.com/tumblr/docs/issues/115
                # Thus, the next two bits are untested and are broken at least for
                # lists (this should be <li><ul><li><ul>... not <ul><ul>...), but since
                # it's not possible to make a post that triggers this I'm ignoring it
                # for now.

                if indent_delta > 0:
                    # If we're going up an indent, add a closing tag to the stack:
                    block.prefix = block.prefix + (
                        f"<{subtype_wrappers[subtype]}>" * (indent_delta_abs)
                    )
                    closing_tags.extend(
                        [f"</{subtype_wrappers[subtype]}>"] * (indent_delta_abs)
                    )
                    type_stack.extend([subtype] * (indent_delta_abs))

                elif indent_delta < 0:
                    # If we're going down an indent, pop some closing tags and
                    # add them to the prefix of the current block.
                    _closing = ""
                    for _ in range((indent_delta_abs)):
                        _closing += closing_tags.pop()
                        type_stack.pop()
                    block.prefix = _closing + block.prefix

            indent_level += indent_delta
            n += 1

        if closing_tags:
            _closing = ""
            for _ in range(len(closing_tags)):
                _closing += closing_tags.pop()
                type_stack.pop()
            self.blocks[-1].suffix += _closing

    def to_html(self, wrap_blocks=False):
        self._reset_annotations()
        self._assign_html_indents(wrap_blocks=wrap_blocks)

        if wrap_blocks:
            ret = ""

            row_start = []
            row_lengths = {}
            row_end = []
            for lay in self.layout:
                if lay.layout_type != "rows":
                    continue
                for row in lay.rows:
                    if len(row) > 1:
                        row_start.append(row[0])
                        row_lengths[row[0]] = len(row)
                        row_end.append(row[-1])

            n = len(self.ask_blocks)
            in_row = False
            for block in self.blocks[len(self.ask_blocks) :]:
                base_block = (
                    block.base_block if isinstance(block, NPFBlockAnnotated) else block
                )

                if n in row_start:
                    ret += f'<div class="row-multiple row-{row_lengths[n]}">'
                    in_row = True
                if in_row and base_block.attribution:
                    ret += (
                        "<div>"
                        + block.to_html()
                        + base_block.attribution.to_html()
                        + "</div>"
                    )
                else:
                    ret += block.to_html()
                    if not in_row and base_block.attribution:
                        ret += base_block.attribution.to_html()
                if n in row_end:
                    ret += "</div>"
                    in_row = False
                n += 1
        else:
            ret = "".join(
                [block.to_html() for block in self.blocks[len(self.ask_blocks) :]]
            )

        if len(self.ask_blocks) > 0:
            ret = (
                f'<div class="question"><div class="question-header"><strong class="asking-name">{html.escape(self.ask_content.asking_name)}</strong> asked:</div><div class="question-content">'
                + "".join([block.to_html() for block in self.ask_blocks])
                + "</div></div>"
                + ret
            )

        return ret

    def to_markdown(
        self, placeholders: bool = False, skip_single_placeholders: bool = False
    ):
        self._reset_annotations()

        blocks = self.blocks[len(self.ask_blocks) :]

        ret = ""
        if placeholders and skip_single_placeholders and not self.ask_blocks:
            block_counts = {"image": 0, "video": 0}

            for block in blocks:
                md = block.to_markdown(placeholders=True)
                try:
                    base = block.base_block
                except AttributeError:
                    base = block
                if isinstance(base, NPFImageBlock) and md.strip() == "(image)":
                    block_counts["image"] += 1
                elif isinstance(base, NPFVideoBlock) and md.strip() == "(video)":
                    block_counts["video"] += 1

            if (block_counts["image"] == 1 or block_counts["video"] == 1) and not (
                block_counts["image"] > 0 and block_counts["video"] > 0
            ):
                try:
                    blocks[0].base_block
                    blocks[-1].base_block
                except AttributeError:
                    pass
                else:
                    if block_counts["image"] == 1:
                        banned_type = NPFImageBlock
                        if isinstance(blocks[0].base_block, banned_type):
                            del blocks[0]
                        elif isinstance(blocks[-1].base_block, banned_type):
                            del blocks[-1]
                    elif block_counts["video"] == 1:
                        banned_type = NPFVideoBlock
                        if isinstance(blocks[0].base_block, banned_type):
                            del blocks[0]
                        elif isinstance(blocks[-1].base_block, banned_type):
                            del blocks[-1]

        ret = "".join(
            [block.to_markdown(placeholders=placeholders) for block in blocks]
        )

        if len(self.ask_blocks) > 0:
            ret = (
                f"💬 {self.ask_content.asking_name} asked:"
                + "".join(
                    [
                        block.to_markdown(placeholders=placeholders)
                        for block in self.ask_blocks
                    ]
                )
                + "\n"
                + ret
            )

        return ret

    @property
    def ask_content(self) -> Optional["NPFAsk"]:
        if self.has_ask:
            return NPFAsk.from_parent_content(self)


class NPFAsk(NPFContent):
    def __init__(
        self,
        blocks: List[NPFBlock],
        ask_layout: NPFLayout,
        avatar: Optional[str] = None,
    ):
        super().__init__(
            blocks=blocks, layout=[], blog_name=ask_layout.asking_name, avatar=avatar
        )

    @property
    def asking_name(self) -> str:
        return self.blog_name

    @staticmethod
    def from_parent_content(parent_content: NPFContent) -> Optional["NPFAsk"]:
        if parent_content.has_ask:
            return NPFAsk(
                blocks=deepcopy(parent_content.ask_blocks),
                ask_layout=deepcopy(parent_content.ask_layout),
            )


class TumblrPostBase:
    def __init__(
        self,
        blog_name: str,
        id: int,
        content: TumblrContentBase,
        genesis_post_id: Optional[int] = None,
    ):
        self._blog_name = blog_name
        self._content = content
        self._id = id
        self._genesis_post_id = genesis_post_id

    @property
    def blog_name(self):
        return self._blog_name

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    @property
    def genesis_post_id(self):
        return self._content


class TumblrReblogInfo:
    def __init__(
        self,
        reblogged_from: str,
        reblogged_by: str,
    ):
        self._reblogged_from = reblogged_from
        self._reblogged_by = reblogged_by

    @staticmethod
    def from_payload(payload: dict) -> Optional["TumblrReblogInfo"]:
        if "reblogged_from_id" not in payload:
            return None
        return TumblrReblogInfo(
            reblogged_from=payload["reblogged_from_name"],
            reblogged_by=_get_blogname_from_payload(payload),
        )

    @property
    def reblogged_from(self):
        return self._reblogged_from

    @property
    def reblogged_by(self):
        return self._reblogged_by


class TumblrPost(TumblrPostBase):
    def __init__(
        self,
        blog_name: str,
        content: TumblrContentBase,
        tags: Optional[List[str]],
    ):
        self._blog_name = blog_name
        self._content = content
        self._tags = tags

    @property
    def tags(self):
        return self._tags

    @property
    def id(self):
        return self._content.id

    @property
    def is_submission(self):
        return self._content.is_submission

    @is_submission.setter
    def is_submission(self, value: bool):
        self._content.is_submission = value

    @property
    def submitted_by(self):
        return self._content.submitted_by

    @submitted_by.setter
    def submitted_by(self, value: bool):
        self._content.submitted_by = value

    @property
    def genesis_post_id(self):
        return self._content.genesis_post_id

    def to_html(self, wrap_blocks=False) -> str:
        return sanitize_html(self._content.to_html(wrap_blocks=wrap_blocks))

    def to_markdown(
        self, placeholders: bool = False, skip_single_placeholders: bool = False
    ) -> str:
        return self._content.to_markdown(
            placeholders=placeholders, skip_single_placeholders=skip_single_placeholders
        )


class TumblrThreadInfo:
    def __init__(
        self,
        title: str,
        images: Optional[List[NPFMediaList]],
        videos: Optional[List[NPFMediaList]],
        audio: Optional[List[NPFMediaList]],
        other_blocks: Optional[List[NPFBlock]],
        has_formatting: bool,
    ):
        self._title = title
        self._images = images
        self._videos = videos
        self._audio = audio
        self._other_blocks = other_blocks
        self._has_formatting = has_formatting

    @staticmethod
    def from_payload(payload: dict, posts: List) -> "TumblrThreadInfo":
        title = payload["title"] if "title" in payload else ""
        images = []
        videos = []
        audio = []
        other_blocks = []
        has_formatting = False
        for post in posts:
            raw_blocks = [
                block.base_block if isinstance(block, NPFBlockAnnotated) else block
                for block in post.content.blocks
            ]
            for block in raw_blocks:
                if isinstance(block, NPFTextBlock):
                    if block.formatting or block.subtype_name != "no_subtype":
                        has_formatting = True
                elif isinstance(block, NPFLinkBlock):
                    other_blocks.append(block)
                elif isinstance(block, NPFPollBlock):
                    other_blocks.append(block)
                elif isinstance(block, NPFReadMoreBlock):
                    other_blocks.append(block)
                elif block.media:
                    if isinstance(block, NPFImageBlock):
                        images.append(block.media)
                    elif isinstance(block, NPFVideoBlock):
                        videos.append((block.media, block.poster))
                    elif isinstance(block, NPFAudioBlock):
                        audio.append((block.media, block.poster))
                    else:
                        other_blocks.append(block)
                else:
                    other_blocks.append(block)

        return TumblrThreadInfo(
            title, images, videos, audio, other_blocks, has_formatting
        )

    @property
    def title(self):
        return self._title

    @property
    def images(self):
        return self._images

    @property
    def videos(self):
        return self._videos

    @property
    def audio(self):
        return self._audio

    @property
    def other_blocks(self):
        return self._other_blocks

    @property
    def has_formatting(self):
        return self._has_formatting


class TumblrThread:
    def __init__(
        self,
        id: str,
        blog_name: str,
        avatar: str,
        posts: List[TumblrPost],
        timestamp: int,
        thread_info: TumblrThreadInfo,
        reblog_info: Optional[TumblrReblogInfo],
        unroll: bool,
        is_submission: bool,
        submitted_by: Optional[str],
    ):
        self._id = id
        self._blog_name = blog_name
        self._avatar = avatar
        self._posts = posts
        self._timestamp = timestamp
        self._thread_info = thread_info
        self._reblog_info = reblog_info
        self.unroll = unroll
        self._is_submission = is_submission
        self._submitted_by = submitted_by

    @property
    def posts(self):
        return self._posts

    @property
    def id(self):
        return self._id

    @property
    def blog_name(self):
        return self._blog_name

    @property
    def avatar(self):
        return self._avatar

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def thread_info(self):
        return self._thread_info

    @property
    def reblog_info(self):
        return self._reblog_info

    @property
    def reblogged_from(self):
        if self._reblog_info:
            return self._reblog_info.reblogged_from
        return ""

    @property
    def reblogged_by(self):
        if self._reblog_info:
            return self._reblog_info.reblogged_by
        return ""

    @property
    def is_submission(self):
        return self._is_submission

    @property
    def submitted_by(self):
        return self._submitted_by

    @staticmethod
    def from_payload(payload: dict, unroll: bool = False) -> "TumblrThread":
        post_payloads = payload.get("trail", []) + [payload]
        posts = [
            TumblrPost(
                blog_name=_get_blogname_from_payload(post_payload),
                content=NPFContent.from_payload(post_payload, unroll=unroll),
                tags=post_payload.get("tags", []),
            )
            for post_payload in post_payloads
        ]
        id = payload["id"]
        blog_name = _get_blogname_from_payload(payload)
        avatar = _get_avatar_from_payload(payload)
        thread_info = TumblrThreadInfo.from_payload(payload, posts)
        reblog_info = TumblrReblogInfo.from_payload(payload)
        is_submission = payload.get("is_submission", False)
        submitted_by = payload.get("post_author", None)
        if is_submission and submitted_by:
            posts[-1].is_submission = True
            posts[-1].submitted_by = submitted_by

        timestamp = payload["timestamp"]

        return TumblrThread(
            id,
            blog_name,
            avatar,
            posts,
            timestamp,
            thread_info,
            reblog_info,
            unroll,
            is_submission,
            submitted_by,
        )

    @staticmethod
    def _format_post_as_quoting_previous(
        post: TumblrPost, prev: TumblrPost, quoted: str
    ) -> str:
        return f"{prev.content.legacy_prefix_link}<blockquote>{quoted}</blockquote>{post.to_html()}"

    def to_html(self) -> str:
        result = ""

        post_part = self.posts[0].to_html()
        result += post_part

        for prev, post in zip(self.posts[:-1], self.posts[1:]):
            result = TumblrThread._format_post_as_quoting_previous(post, prev, result)

        return sanitize_html(result)

    def to_markdown(
        self, placeholders: bool = False, skip_single_placeholders: bool = False
    ) -> str:
        ret = ""

        for post in self.posts:
            ret += "{post.blogname}:\n"
            for block in post.blocks:
                ret += block.to_markdown(
                    placeholders=placeholders,
                    skip_single_placeholders=skip_single_placeholders,
                )

        return ret

    @property
    def ask_content(self) -> Optional[NPFAsk]:
        op_content = self.posts[0].content
        if op_content.has_ask:
            return op_content.ask_content
