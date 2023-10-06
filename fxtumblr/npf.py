# NPF to HTML converter. Taken from pytumblr2 and extended for fxtumblr's needs:
# https://github.com/nostalgebraist/pytumblr2/blob/master/pytumblr2/format_conversion/npf2html.py


from typing import List, Optional, Tuple
from collections import defaultdict
from itertools import zip_longest
from copy import deepcopy
from markdownify import markdownify


def _get_blogname_from_payload(post_payload):
    """retrieves payload --> broken_blog_name, or payload --> blog --> name"""
    if "broken_blog_name" in post_payload:
        return post_payload["broken_blog_name"]
    return post_payload["blog"]["name"]


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
            return f"<p><h1>{text_or_break}</h1></p>"
        elif self.subtype == "heading2":
            return f"<p><h2>{text_or_break}</h2></p>"
        elif self.subtype == "ordered-list-item":
            return f"<li>{text}</li>"
        elif self.subtype == "unordered-list-item":
            return f"<li>{text}</li>"
        # These match the standard classes used in Tumblr's CSS:
        elif self.subtype == "chat":
            text_or_break = text_or_break.replace("\n\n", '</p><p class="npf_chat">')
            return f'<p class="npf_chat">{text_or_break}</p>'
        elif self.subtype == "quote":
            text_or_break = text_or_break.replace("\n\n", '</p><p class="npf_quote">')
            return f'<p class="npf_quote">{text_or_break}</p>'
        elif self.subtype == "quirky":
            text_or_break = text_or_break.replace("\n\n", '</p><p class="npf_quirky">')
            return f'<p class="npf_quirky">{text_or_break}</p>'
        elif len(text) == 0:
            return ""
        else:
            text_or_break = text_or_break.replace("\n\n", "</p><p>")
            return f"<p>{text_or_break}</p>"

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
            return NPFVideoBlock.from_payload(payload)
        elif payload.get("type") == "audio":
            return NPFAudioBlock.from_payload(payload)
        else:
            raise ValueError(payload.get("type"))


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
        else:
            insertions = [formatting.to_html() for formatting in self.formatting]

        insert_ix_to_inserted_text = defaultdict(list)
        for insertion in insertions:
            insert_ix_to_inserted_text[insertion["start"]].append(
                insertion["start_insert"]
            )
            insert_ix_to_inserted_text[insertion["end"]].append(insertion["end_insert"])

        split_ixs = {0, len(self.text)}
        split_ixs.update(insert_ix_to_inserted_text.keys())
        split_ixs = sorted(split_ixs)

        accum = []

        for ix1, ix2 in zip_longest(split_ixs, split_ixs[1:], fillvalue=split_ixs[-1]):
            accum.extend(insert_ix_to_inserted_text[ix1])
            accum.append(self.text[ix1:ix2])

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
    ):
        if not media and not embed_html:
            raise ValueError("Either media or embed_html must be provided")
        self._media = NPFMediaList(media)
        self._alt_text = alt_text
        self._embed_html = embed_html
        self._poster = NPFMediaList(poster) if poster else None

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


class NPFImageBlock(NPFMediaBlock):
    @staticmethod
    def from_payload(payload: dict) -> "NPFImageBlock":
        return NPFImageBlock(media=payload["media"], alt_text=payload.get("alt_text"))

    def to_html(self, target_width: int = 640) -> str:
        selected_size = self.media._pick_one_size(target_width)

        original_dimensions_attrs_str = ""
        if self.media.original_dimensions is not None:
            orig_w, orig_h = self.media.original_dimensions
            original_dimensions_attrs_str = (
                f' data-orig-height="{orig_h}" data-orig-width="{orig_w}"'
            )

        img_tag = (
            f"<img src=\"{selected_size['url']}\"{original_dimensions_attrs_str}/>"
        )

        figure_tag = f'<figure class="tmblr-full"{original_dimensions_attrs_str}>{img_tag}</figure>'

        return figure_tag

    def to_markdown(self, target_width: int = 640, placeholders: bool = False) -> str:
        if placeholders:
            return "\n(image)"

        selected_size = self.media._pick_one_size(target_width)

        return f"\n![Image]({selected_size['url']})"


class NPFVideoBlock(NPFMediaBlock):
    @staticmethod
    def from_payload(payload: dict) -> "NPFVideoBlock":
        return NPFVideoBlock(
            media=[payload["media"]] if "media" in payload else [],
            alt_text=payload.get("alt_text"),
            poster=payload["poster"] if "poster" in payload else None,
            embed_html=payload["embed_html"] if "embed_html" in payload else "",
        )

    def to_html(self, target_width: int = 640) -> str:
        if self.embed_html:
            return self.embed_html

        selected_size_poster = self.poster._pick_one_size(target_width)

        original_dimensions_attrs_str = ""
        if self.media.original_dimensions is not None:
            orig_w, orig_h = self.media.original_dimensions
            original_dimensions_attrs_str = (
                f' data-orig-height="{orig_h}" data-orig-width="{orig_w}"'
            )

        video_tag = f"<video poster=\"{selected_size_poster['url']}\" controls=\"controls\"{original_dimensions_attrs_str}><source src=\"{self.media.media[0]['url']}\" type=\"video/mp4\"></video>"

        figure_tag = f'<figure class="tmblr-full"{original_dimensions_attrs_str}>{video_tag}</figure>'

        return figure_tag

    def to_markdown(self, target_width: int = 640, placeholders: bool = False) -> str:
        if self.embed_html:
            if placeholders:
                return "\n(video embed)"
            return self.embed_html
        if placeholders:
            return "\n(video)"

        selected_size_poster = self.poster._pick_one_size(target_width)

        return f"\n![Video thumbnail]({selected_size_poster['url']})"


class NPFAudioBlock(NPFMediaBlock):
    @staticmethod
    def from_payload(payload: dict) -> "NPFAudioBlock":
        return NPFAudioBlock(
            media=[payload["media"]] if "media" in payload else [],
            alt_text=payload.get("alt_text"),
            poster=payload["poster"] if "poster" in payload else None,
            embed_html=payload["embed_html"] if "embed_html" in payload else "",
        )

    def to_html(self, target_width: int = 640) -> str:
        if self.embed_html:
            return self.embed_html

        original_dimensions_attrs_str = ""
        if self.media.original_dimensions is not None:
            orig_w, orig_h = self.media.original_dimensions
            original_dimensions_attrs_str = (
                f' data-orig-height="{orig_h}" data-orig-width="{orig_w}"'
            )

        audio_tag = f"<audio src=\"{self.media.media[0]['url']}\" controls=\"controls\" muted=\"muted\"{original_dimensions_attrs_str}/>"

        figure_tag = f'<figure class="tmblr-full"{original_dimensions_attrs_str}>{audio_tag}</figure>'

        return figure_tag

    def to_markdown(self, target_width: int = 640, placeholders: bool = False) -> str:
        if self.embed_html:
            if placeholders:
                return "\n(audio embed)"
            return self.embed_html
        if placeholders:
            return "\n(audio)"

        # todo: return poster
        return "\n(audio)"


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


class NPFRow:
    def __init__(
        self,
        blocks: List[int],
        mode: Optional[NPFLayoutMode] = None,
    ):
        self._blocks = blocks
        self._mode = mode

    @property
    def blocks(self):
        return self._blocks

    @property
    def mode(self):
        return self._mode

    @staticmethod
    def from_payload(payload: dict) -> "NPFRow":
        return NPFRow(blocks=payload["blocks"], mode=payload.get("mode"))


class NPFLayoutRows(NPFLayout):
    def __init__(
        self,
        rows: List[NPFRow],
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
        id: Optional[int] = None,
        genesis_post_id: Optional[int] = None,
        post_url: Optional[str] = None,
    ):
        self.raw_blocks = [
            block if isinstance(block, NPFBlockAnnotated) else NPFBlockAnnotated(block)
            for block in blocks
        ]
        self.layout = layout
        self.blog_name = blog_name
        self.id = id
        self.genesis_post_id = genesis_post_id
        self._post_url = post_url

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
        if len(self.layout) == 0:
            return self.raw_blocks
        else:
            # TODO: figure out how to handle truncate_after
            ordered_block_ixs = []
            ask_ixs = set()
            ask_ixs_to_layouts = {}
            for layout_entry in self.layout:
                if layout_entry.layout_type == "rows":
                    for row_ixs in layout_entry.rows:
                        # note: this doesn't properly handle multi-column rows
                        # TODO: handle multi-column rows

                        # note: deduplication here is needed b/c of april 2021 tumblr npf ask bug
                        deduped_ixs = [
                            ix for ix in row_ixs if ix not in ordered_block_ixs
                        ]
                        ordered_block_ixs.extend(deduped_ixs)
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
            return [
                self.raw_blocks[ix].as_ask_block(ask_layout=ask_ixs_to_layouts[ix])
                if ix in ask_ixs
                else self.raw_blocks[ix]
                for ix in ordered_block_ixs
            ]

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

    @staticmethod
    def from_payload(
        payload: dict, raise_on_unimplemented: bool = False
    ) -> "NPFContent":
        blocks = []
        for bl in payload["content"]:
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

        blog_name = _get_blogname_from_payload(payload)

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

        post_url = payload.get("post_url")
        return NPFContent(
            blocks=blocks,
            layout=layout,
            blog_name=blog_name,
            id=id,
            genesis_post_id=genesis_post_id,
            post_url=post_url,
        )

    def _reset_annotations(self):
        for bl in self.blocks:
            bl.reset_annotations()
        self.blocks = self._make_blocks()

    def _assign_html_indents(self):
        # This is what the block is wrapped in. The actual contents of the
        # block itself are wrapped in the <p>, <li> elements as needed.
        subtype_wrappers = {
            "indented": "blockquote",
            "ordered-list-item": "ol",
            "unordered-list-item": "ul",
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

    def to_html(self):
        self._reset_annotations()
        self._assign_html_indents()

        ret = "".join(
            [block.to_html() for block in self.blocks[len(self.ask_blocks) :]]
        )
        if len(self.ask_blocks) > 0:
            ret = (
                f'<div class="question"><p class="question-header"><strong class="asking-name">{self.ask_content.asking_name}</strong> asked:</p>\n'
                + "".join([block.to_html() for block in self.ask_blocks])
                + "</div>"
                + ret
            )

        return ret

    def to_markdown(self, placeholders: bool = False):
        self._reset_annotations()

        ret = "".join(
            [
                block.to_markdown(placeholders=placeholders)
                for block in self.blocks[len(self.ask_blocks) :]
            ]
        )
        if len(self.ask_blocks) > 0:
            ret = (
                f"{self.ask_content.asking_name} asked:\n"
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
    def __init__(self, blocks: List[NPFBlock], ask_layout: NPFLayout):
        super().__init__(
            blocks=blocks,
            layout=[],
            blog_name=ask_layout.asking_name,
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
    def genesis_post_id(self):
        return self._content.genesis_post_id

    def to_html(self) -> str:
        return self._content.to_html()

    def to_markdown(self, placeholders: bool = False) -> str:
        return self._content.to_markdown(placeholders=placeholders)


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
        # polls = []
        other_blocks = []
        has_formatting = False
        for post in posts:
            raw_blocks = [
                block.base_block if isinstance(block, NPFBlockAnnotated) else block
                for block in post.content.blocks
            ]
            for block in raw_blocks:
                if isinstance(block, NPFTextBlock):
                    if block.formatting:
                        has_formatting = True
                elif block.media:
                    if isinstance(block, NPFImageBlock):
                        images.append(block.media)
                    elif isinstance(block, NPFVideoBlock):
                        videos.append((block.media, block.poster))
                    elif isinstance(block, NPFAudioBlock):
                        audio.append((block.media, block.poster))
                    else:
                        other_blocks.append(block)
                # elif isinstance(block, NPFPollBlock):
                # 	polls.append(block)
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
        posts: List[TumblrPost],
        timestamp: int,
        thread_info: TumblrThreadInfo,
        reblog_info: Optional[TumblrReblogInfo],
    ):
        self._id = id
        self._blog_name = blog_name
        self._posts = posts
        self._timestamp = timestamp
        self._thread_info = thread_info
        self._reblog_info = reblog_info

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

    @staticmethod
    def from_payload(payload: dict) -> "TumblrThread":
        post_payloads = payload.get("trail", []) + [payload]
        posts = [
            TumblrPost(
                blog_name=_get_blogname_from_payload(post_payload),
                content=NPFContent.from_payload(post_payload),
                tags=post_payload.get("tags", []),
            )
            for post_payload in post_payloads
        ]
        id = payload["id"]
        blog_name = _get_blogname_from_payload(payload)
        thread_info = TumblrThreadInfo.from_payload(payload, posts)
        reblog_info = TumblrReblogInfo.from_payload(payload)

        timestamp = payload["timestamp"]

        return TumblrThread(id, blog_name, posts, timestamp, thread_info, reblog_info)

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

        return result

    def to_markdown(self, placeholders: bool = False) -> str:
        return "".join(
            [
                "".join(
                    [
                        block.to_markdown(placeholders=placeholders)
                        for block in posts.blocks
                    ]
                )
                for post in self.posts
            ]
        )

    @property
    def ask_content(self) -> Optional[NPFAsk]:
        op_content = self.posts[0].content
        if op_content.has_ask:
            return op_content.ask_content
