"""
Contains code for creating the embed.
"""

import itertools
import pytumblr
from quart import request, render_template, redirect

from . import app
from .cache import post_needs_caching, cache_post, get_cached_post
from .config import APP_NAME, BASE_URL, config
from .parser import get_trail
from .render import render_thread
from .npf2html import TumblrThread

app.config['EXPLAIN_TEMPLATE_LOADING'] = True

tumblr = pytumblr.TumblrRestClient(
    config['tumblr_consumer_key'],
    config['tumblr_consumer_secret'],
    None, None,
)


@app.route('/<string:blogname>/<int:postid>')
@app.route('/<string:blogname>/<int:postid>/<string:summary>')
async def generate_embed(blogname: str, postid: int, summary: str = None):
    should_render = False
    needs_caching = post_needs_caching(blogname, postid)

    if needs_caching:
        _post = tumblr.posts(blogname=blogname, id=postid, reblog_info=True, npf=True)
        if not _post or 'posts' not in _post or not _post['posts']:
            return await parse_error(_post, post_url=f'https://www.tumblr.com/{blogname}/{postid}')
        post = _post['posts'][0]
        needs_caching = cache_post(blogname, postid, _post)
    else:
        _post = get_cached_post(blogname, postid)
        post = _post['posts'][0]

    from pprint import pprint
    pprint(post)

    #return TumblrThread.from_payload(post).to_html()
    return await render_template('render.html', thread=TumblrThread.from_payload(post))

    title = None
    if 'title' in post:
        title = post['title']

    trail = await get_trail(post)

    card_type = 'tweet'

    # In general, videos can be prepended only to the first post in the trail,
    # but some clever folks have figured out how to put them in a reblog:
    # https://tumblr.com/punkitt-is-here/723305358401077248
    # So, we have to check *all* posts. Oops.
    video = None
    for tpost in trail:
        if tpost['type'] == 'video':
            card_type = 'video'
            video = tpost['video']
            if 'video' in request.args:
                return redirect(video['url'])

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
        image = images[0]
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
        if len(trail) > 1:
            description += f'\n\n{info["blogname"]}:\n'
        if n == 0 and title:
            description += f'# {title}\n\n'
        description += info['content']
        n += 1
    description = description.strip()

    if 'tags' in post and post['tags']:
        description += '\n\n(#' + ' #'.join(post['tags']) + ')'

    # Truncate description (a maximum of 349 characters can be displayed, 256 for video desc)
    if video:
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
        header = reblog["by"] + " 🔁 " + reblog["from"]
    else:
        header = trail[-1]["blogname"]

    if not should_render:
        for trailpost in trail:
            if '<span class="npf_' in trailpost['content_html'] or \
                    '<span style="color:' in trailpost['content_html'] or \
                    '<p class="npf_' in trailpost['content_html']:
                should_render = True
                break

    if config['renders_enable'] and should_render:
        image = await render_thread(post, trail, reblog, force_new_render=needs_caching)
        card_type = 'summary_large_image'
        if video:
            description = f'TIP: You can get the raw video by pasting in the following link: {BASE_URL}/{post["blog_name"]}/{post["id"]}?video'
        else:
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


async def parse_error(info: dict, post_url: str = None):
    """Parses error returned by Tumblr API."""
    if not info or 'meta' not in info:
        return await render_template('error.html',
                app_name=APP_NAME,
                msg="Internal server error."), 500

    if info['meta']['status'] == 404:
        if 'errors' in info and info['errors'] and info['errors'][0]['code'] == 4012:
            return await render_template('locked.html',
                app_name=APP_NAME, posturl=post_url)
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
