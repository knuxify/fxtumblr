"""
Contains code for creating the embed.
"""

import itertools
import pytumblr
from quart import request, render_template

from . import app
from .config import APP_NAME, BASE_URL, config
from .parser import get_trail
from .render import render_thread

tumblr = pytumblr.TumblrRestClient(
    config['tumblr_consumer_key'],
    config['tumblr_consumer_secret'],
    None, None,
)


@app.route('/<string:blogname>/<int:postid>')
@app.route('/<string:blogname>/<int:postid>/<string:summary>')
async def generate_embed(blogname: str, postid: int, summary: str = None):
    should_render = False

    _post = tumblr.posts(blogname=blogname, id=postid, reblog_info=True)
    if not _post or 'posts' not in _post or not _post['posts']:
        return await parse_error(_post)
    post = _post['posts'][0]

    title = None
    if 'summary' in _post:
        title = _post['summary']

    trail = await get_trail(post)

    card_type = 'tweet'

    # Videos can only be appended to the first post in the trail,
    # so we only check there.
    video = None
    if trail[0]['type'] == 'video':
        card_type = 'video'
        video = trail[0]['video']

    # Get image
    images = list(itertools.chain.from_iterable(
        [post['images'] for post in trail if 'images' in post]
    ))

    if len(images) == 0:
        image = _post['blog']['avatar'][0]['url']
    elif len(images) == 1:
        image = images[0]
        if not card_type == 'video':
            card_type = 'summary_large_image'
    else:
        should_render = True

    reblog = {"by": '', "from": ''}
    try:
        reblog['from'] = post['reblogged_from_name']
        reblog['by'] = post['blog_name']
    except KeyError:
        pass

    description = ''
    n = 0
    for info in trail:
        description += f'\n\n{info["blogname"]}:\n'
        if n == 0 and title:
            description += f'# {title}\n\n'
        description += info['content']
        n += 1
    description = description.strip()

    # Truncate description (a maximum of 349 characters can be displayed, 256 for video desc)
    if trail[0]['type'] == 'video':
        truncate_placeholder = '... (click to see full thread)'
        max_desc_length = 256 - len(truncate_placeholder)
    else:
        truncate_placeholder = '... (see full thread)'
        max_desc_length = 349 - len(truncate_placeholder)

    if len(description) > max_desc_length:
        description = description[:max_desc_length] + truncate_placeholder
        should_render = True

    op = trail[-1]['blogname']
    miniheader = op + f' ({post["note_count"]} notes)'

    if reblog['from']:
        header = reblog["from"] + " 🔁 " + reblog["by"]
    else:
        header = trail[-1]["blogname"]

    if config['renders_enable'] and should_render:
        image = await render_thread(post, trail, reblog)
        card_type = 'summary_large_image'
        description = ''
        video = None
    else:
        should_render = False

    return await render_template('card.html',
        image=image,
        card_type=card_type,
        posturl=post['post_url'],
        header=header,
        miniheader=miniheader,
        op=op,
        video=video,
        desc=description,
        app_name=APP_NAME,
        base_url=BASE_URL,
        is_rendered=should_render
    )


async def parse_error(info: dict):
    """Parses error returned by Tumblr API."""
    if not info or 'meta' not in info:
        return await render_template('error.html',
                app_name=APP_NAME,
                msg="Internal server error."), 500

    if info['meta']['status'] == 404:
        if 'errors' in info and info['errors'] and info['errors'][0]['code'] == 4012:
            return await render_template('error/locked.html',
                app_name=APP_NAME,
                msg="Profile is only available for logged-in users."), 403
        return await render_template('error.html',
            app_name=APP_NAME,
            msg="Post not found."), 404

    return await render_template('error.html',
            app_name=APP_NAME,
            msg="Internal server error."), 500


@app.route('/oembed.json')
async def oembed_json():
    out = {
        "type": request.args.get("ttype", None),
        "version": "1.0",
        "provider_name": "fxtumblr",
        "provider_url": "https://github.com/knuxify/fxtumblr",
        "title": request.args.get("op", None),
        "author_name": request.args.get("desc", None),
        "author_url": request.args.get("link", None)
    }

    return out
