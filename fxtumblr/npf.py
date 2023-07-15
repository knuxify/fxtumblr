"""
Contains code for handling Neue Post Format (NPF) posts.
"""

NPF_HTML_REPLACES = {
    'paragraph': ('<p>', '</p>'),

    'bold': ('<strong>', '</strong>'),
    'italic': ('<em>', '</em>'),
    'strikethrough': ('<s>', '</s>'),
    'small': ('<small>', '</small>'),

    'heading1': ('<h1>', '</h1>'),
    'heading2': ('<h2>', '</h2>'),
    'quirky': ('<span class="npf_quirky">', '</span>'),
    'quote': ('<span class="npf_quote">', '</span>'),
    'chat': ('<span class="npf_chat">', '</span>'),

    'color': ('<span style="color: #{color}">', '</span>'),
    'color_ff492f': ('<span class="npf_color_joey">', '</span>'),
    'color_ff8a00': ('<span class="npf_color_monica">', '</span>'),
    'color_7c5cff': ('<span class="npf_color_chandler">', '</span>'),
    'color_e8d73a': ('<span class="npf_color_phoebe">', '</span>'),
    'color_00b8ff': ('<span class="npf_color_rachel">', '</span>'),
    'color_00cf35': ('<span class="npf_color_ross">', '</span>'),
    'color_ff62ce': ('<span class="npf_color_niles">', '</span>'),
    'color_001935': ('<span class="npf_color_frasier">', '</span>'),
    'color_000c1a': ('<span class="npf_color_mr_big">', '</span>'),

    'link': ('<a href="{url}">', '</a>')
}

NPF_MARKDOWN_REPLACES = {
    'paragraph': ('', '\n'),

    'bold': ('**', '**'),
    'italic': ('*', '*'),
    'strikethrough': ('~', '~'),
    'small': ('*', '*'),

    'heading1': ('# ', ''),
    'heading2': ('# ', ''),
    'quirky': ('*', '*'),
    'quote': ('> ', ''),
    'chat': ('`', '`'),

    'color': ('*', '*'),
    'link': ('[', ']({url}')
}


def npf_handle_text(block: dict, markdown: bool = False) -> str:
    """Handles an NPF text block."""
    out = block['text']

    if markdown:
        npf_replaces = NPF_MARKDOWN_REPLACES
    else:
        npf_replaces = NPF_HTML_REPLACES

    if 'formatting' in block:
        format_inserts = {}
        for format in block['formatting']:
            rep = npf_replaces[format['type']]

            for pos in ('start', 'end'):
                i = ('start', 'end').index(pos)
                if format[pos] not in format_inserts:
                    format_inserts[format[pos]] = []
                if format['type'] == 'link':
                    format_inserts[format[pos]].append(rep[i].replace('{url}', format['url']))
                elif format['type'] == 'mention':
                    format_inserts[format[pos]].append(rep[i].replace('{url}', format['blog']['url']))
                else:
                    format_inserts[format[pos]].append(rep[i])

        n = 0
        out = ''
        # Technically, in the case of HTML, overlapping elements should be
        # handled, but the browser already fixes them up for us so why
        # bother doing it ourselves?
        for char in block['text']:
            if n in format_inserts:
                for finsert in format_inserts[n]:
                    out += finsert

            out += char
            n += 1

    if 'subtype' in block:
        if block['subtype'] in npf_replaces:
            rep = npf_replaces[block['subtype']]
            out = rep[0] + out + rep[1]

    out = npf_replaces['paragraph'][0] + out + npf_replaces['paragraph'][1]

    return out


def npf_to_html(post: dict) -> str:
    """Takes an NPF post dict and converts its contents into HTML."""
    out = []

    for block in post['content']:
        if block['type'] == 'text':
            out.append(npf_handle_text(block))

        elif block['type'] == 'image':
            image = None
            for media in block['media']:
                if media['width'] < 540:
                    if 'poster' in media:
                        image = media['poster']['url']
                    else:
                        image = media['url']
                    break
            if not image and block['media']:
                image = media[0]['url']
            out.append(f'<p><figure class="tmblr-full"><img src="{image}"></figure></p>')

        elif block['type'] == 'video':
            out.append(f'<p><div class="tmblr-full video-thumbnail"><img src="{block["poster"]["url"]}"><svg id="managed-icon__video-play" class="play-button" width="72" role="presentation" fill="#ffffff" viewBox="0 0 24 24"><path d="M20.508 11.126a1.022 1.022 0 010 1.748L7.257 20.788C6.258 21.384 5 20.653 5 19.478V4.522c0-1.176 1.258-1.907 2.257-1.31l13.25 7.913z"></path></svg></div></p>')

        elif block['type'] == 'audio': # TODO
            out.append('<p>(audio)</p>')

    if 'layout' in post:
        for layout in post['layout']:
            if layout['type'] == 'ask':
                out.insert(layout['blocks'][0], f'<div class="question"><p class="question-header">{layout["attribution"]["blog"]["name"]} asked:</p>')
                out.insert(layout['blocks'][1] + 1, '</div>')

    return ''.join(out)


def npf_to_md(post: dict) -> str:
    """Takes an NPF post dict and converts its contents into Markdown."""
    out = []

    if 'broken_blog_name' in post:
        op = post['broken_blog_name']
    else:
        op = post['blog']['name']

    for block in post['content']:
        if block['type'] == 'text':
            out.append(npf_handle_text(block, markdown=True))
        elif block['type'] == 'video':
            out.append('(video) ')
        elif block['type'] == 'image':
            out.append('(image) ')
        elif block['type'] == 'audio':
            out.append('(audio) ')

    if 'layout' in post:
        for layout in post['layout']:
            if layout['type'] == 'ask':
                out.insert(layout['blocks'][0], f'{layout["attribution"]["blog"]["name"]} asked:\n')
                out.insert(layout['blocks'][1] + 1, f'\n{op} replied:\n')

    return ''.join(out)


def npf_to_trailpost(post: dict) -> dict:
    """Returns a post in fxtumblr's internal trail format."""
    out = {
        'type': 'text',
        'content': npf_to_md(post),
        'content_html': npf_to_html(post)
    }

    if 'broken_blog_name' in post:
        out['blogname'] = post['broken_blog_name']
    else:
        out['blogname'] = post['blog']['name']

    for block in post['content']:
        if block['type'] == 'image':
            image = None
            for media in block['media']:
                if media['width'] < 540:
                    if 'poster' in media:
                        image = media['poster']['url']
                    else:
                        image = media['url']
                    break
            if not image and block['media']:
                image = media[0]['url']
            if image:
                if 'images' not in out:
                    out['images'] = []
                out['images'].append(image)

        elif block['type'] == 'video':
            if 'media' not in block:
                # YouTube or other embed
                if 'images' not in out:
                    out['images'] = []
                out['images'].append(block['poster']['url'])
            else:
                out['type'] = 'video'
                out['video'] = {
                    'url': block['media']['url'],
                    'width': block['media']['width'],
                    'height': block['media']['height'],
                    'thumbnail': block['poster']['url']
                }

        elif block['type'] == 'audio':
            if 'media' not in block:
                # SoundCloud or other embed
                if 'images' not in out:
                    out['images'] = []
                out['images'].append(block['poster']['url'])
            else:
                out['type'] = 'audio'
                out['audio'] = {
                    'url': block['media']['url'],
                    'thumbnail': block['poster']['url']
                }

    return out


def npf_get_trail(post: dict) -> list:
    """Returns an fxtumblr internal trail dict."""
    out = []

    if 'trail' in post:
        for element in post['trail']:
            out.append(npf_to_trailpost(element))

    if 'content' in post and post['content']:
        out.append(npf_to_trailpost(post))

    from pprint import pprint
    pprint(out)

    return out
