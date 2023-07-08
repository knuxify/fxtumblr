"""
fxtumblr - makes tumblr embeds more sane
inspired by, and borrowing some code from the original TwitFix
https://github.com/robinuniverse/TwitFix/
"""

from quart import Quart, render_template, redirect, request, send_from_directory
from quart_cors import cors
from werkzeug.middleware.proxy_fix import ProxyFix
import pytumblr
import yaml
from markdownify import markdownify
from bs4 import BeautifulSoup
import os.path
import itertools

# https://stackoverflow.com/questions/2632199/how-do-i-get-the-path-of-the-current-executed-file-in-python
from inspect import getsourcefile
FXTUMBLR_PATH = os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))

# Initial setup to get things up and running

with open('config.yml') as config_file:
    config = yaml.safe_load(config_file)

APP_NAME = config['app_name']
BASE_URL = config['base_url']

app = Quart(__name__)  # Quart app
cors(app)
tumblr = pytumblr.TumblrRestClient(
    config['tumblr_consumer_key'],
    config['tumblr_consumer_secret'],
    None, # config['tumblr_oauth_token'],
    None, # config['tumblr_oauth_secret'],
)

if '127.0.0.1' not in BASE_URL:
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

if config['renders_enable']:
    import tempfile
    import pyppeteer
    RENDERS_PATH = config['renders_path']
    browser = None

    @app.before_serving
    async def setup_browser():
        global browser
        if not browser:
            browser = await pyppeteer.launch()
            # keep alive by leaving blank page open
            await browser.newPage()

    @app.route('/renders/<path:path>')
    async def get_render(path):
        return await send_from_directory(RENDERS_PATH, path)


async def get_post_info(post: dict):
    images = []
    soup = BeautifulSoup(post['content_raw'], 'html.parser')

    info = {
        "blogname": post['blog']['name'],
        "content_html": post['content']
    }

    # Handle video posts. Video posts are just text posts with a <video> tag embedded in a <figure>.
    if soup.find('video'):
        info['type'] = 'video'
        for fig in soup.findAll('figure'):
            if fig.video:
                info['video'] = {
                    "url": next(fig.video.children, None)['src'],
                    "width": fig['data-orig-width'],
                    "height": fig['data-orig-height']
                }
                fig.replaceWith(f'')
        images = [
            info['video']['url']\
                .replace('.mp4', '_frame1.jpg')\
                .replace('va.media.tumblr.com', '64.media.tumblr.com')
        ]

    # Handle audio posts. Audio posts with text or multiple audio files are
    # just text posts with a <audio> tags.
    elif soup.find('audio'):
        info['type'] = 'audio'
        n_audios = len(soup.findAll('audio'))
        n = 0
        for tag in soup.findAll('audio'):
            if n == 0:
                tag.replaceWith(f'({n_audios} audio files attached) ')
            else:
                tag.replaceWith('')
            n += 1
    else:
        info['type'] = 'text'

    if not images:
        for image in soup.findAll('img'):
            images.append(image['src'])
            image.replaceWith(f'(image) ')
    info['images'] = images

    content_html = str(soup)
    info['content'] = markdownify(content_html).strip()
    if not info['content']:
        if info['type'] == 'video':
            info['content'] = '(video)'
        elif info['type'] == 'audio':
            info['content'] = '(audio)'

    return info


async def get_trail(post):
    trail = []

    # Custom handling for audio-only posts (type == 'audio'):
    # since these are not included in the reblog trail, we have to add
    # a little placeholder
    if post['type'] == 'audio':
        info = {
            "type": "audio",
            "content": f"{post['track_name']} (1 audio file attached)",
            "images": [post['album_art']]
        }
        if 'reblogged_root_name' in post:
            info['blogname'] = post['reblogged_root_name']
        else:
            info['blogname'] = post['blog']['name']
        trail.append(info)

    # Custom handling for video-only posts (type == 'video'):
    # since these are not included in the reblog trail, we have to add
    # a little placeholder
    if post['type'] == 'video':
        info = {
            "type": "video",
            "content": "(video)",
            "video": {
                "url": post['video_url'],
                "height": post['thumbnail_height'],
                "width": post['thumbnail_width'],
            },
            "images": [post['thumbnail_url']]
        }
        if 'reblogged_root_name' in post:
            info['blogname'] = post['reblogged_root_name']
        else:
            info['blogname'] = post['blog']['name']
        trail.append(info)

    for p in post['trail']:
        trail.append(await get_post_info(p))

    # Custom handling for image posts (type == 'photo'):
    # the image is not included in the first post in the trail, so we
    # have to add it manually
    if post['type'] == 'photo':
        trail[0]['images'] = [photo['original_size']['url'] for photo in post['photos']]

    return trail


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


async def render_thread(post: dict, trail: dict, reblog_info: dict = {}):
    """
    Takes trail info from the generate_embed function and renders out
    the thread into a picture. Returns a URL to the generated image.
    """
    global browser
    target_filename = f'{post["blog_name"]}-{post["id"]}.png'

    with tempfile.NamedTemporaryFile(suffix='.html') as target_html:
        target_html.write(bytes(await render_template('render.html', trail=trail, fxtumblr_path=FXTUMBLR_PATH, reblog_info=reblog_info), 'utf-8'))

        page = await browser.newPage()
        await page.setViewport({'width': 560, 'height': 300})
        await page.goto(f'file://{target_html.name}')
        await page.screenshot({'path': os.path.join(RENDERS_PATH, target_filename), 'fullPage': True, 'omitBackground': True})
        await page.close()

    return BASE_URL + f'/renders/{target_filename}'


@app.route('/<string:blogname>/<int:postid>')
@app.route('/<string:blogname>/<int:postid>/<string:summary>')
async def generate_embed(blogname: str, postid: int, summary: str = None):
    should_render = False

    _post = tumblr.posts(blogname=blogname, id=postid, reblog_info=True) #, notes_info=True)
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
        if not card_type == 'video':
            card_type = 'summary_large_image'
    elif len(images) == 1:
        image = images[0]
    else:
        should_render = True

    reblog = {"by": '', "from": ''}
    try:
        reblog['from'] = post['reblogged_from_name']
        reblog['by'] = post['blog_name']
    except KeyError as e:
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
            image = image,
            card_type = card_type,
            posturl = post['post_url'],
            header = header,
            miniheader = miniheader,
            op = op,
            video = video,
            desc = description,
            app_name=APP_NAME,
            base_url=BASE_URL,
            is_rendered=should_render
        )


@app.route('/oembed.json')
async def oembed_json():
    out = {
        "type": await request.args.get("ttype", None),
        "version": "1.0",
        "provider_name": "fxtumblr",
        "provider_url": "https://github.com/knuxify/fxtumblr",
        "title": await request.args.get("op", None),
        "author_name": await request.args.get("desc", None),
        "author_url": await request.args.get("link", None)
    }

    return out


@app.route('/')
async def redirect_to_repo():
    return redirect('https://github.com/knuxify/fxtumblr')
