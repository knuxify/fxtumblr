"""
fxtumblr - makes tumblr embeds more sane
inspired by, and borrowing some code from the original TwitFix
https://github.com/robinuniverse/TwitFix/
"""

from flask import Flask, render_template, redirect, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import pytumblr
import yaml
from markdownify import markdownify
from bs4 import BeautifulSoup

# Initial setup to get things up and running

with open('config.yml') as config_file:
    config = yaml.safe_load(config_file)

APP_NAME = config['app_name']
BASE_URL = config['base_url']

app = Flask(__name__)  # Flask app
CORS(app)
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

def get_post_info(post: dict):
    images = []
    soup = BeautifulSoup(post['content_raw'], 'html.parser')

    info = {
        "blogname": post['blog']['name']
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
    info['content'] = markdownify(content_html).rstrip()

    return info


def parse_error(info: dict):
    """Parses error returned by Tumblr API."""
    if not info or 'meta' not in info:
        return render_template('error.html',
                app_name=APP_NAME,
                msg="Internal server error."), 500

    if info['meta']['status'] == 404:
        if 'errors' in info and info['errors'] and info['errors'][0]['code'] == 4012:
            return render_template('error/locked.html',
                app_name=APP_NAME,
                msg="Profile is only available for logged-in users."), 403
        return render_template('error.html',
            app_name=APP_NAME,
            msg="Post not found."), 404

    return render_template('error.html',
            app_name=APP_NAME,
            msg="Internal server error."), 500


@app.route('/<string:blogname>/<int:postid>')
@app.route('/<string:blogname>/<int:postid>/<string:summary>')
def generate_embed(blogname: str, postid: int, summary: str = None):
    _post = tumblr.posts(blogname=blogname, id=postid, reblog_info=True) #, notes_info=True)
    if not _post or 'posts' not in _post or not _post['posts']:
        return parse_error(_post)
    post = _post['posts'][0]

    title = None
    if 'summary' in _post:
        title = _post['summary']

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

    for p in post['trail']:
        trail.append(get_post_info(p))

    # Videos can only be appended to the first post in the trail,
    # so we only check there.
    video = None
    if trail[0]['type'] == 'video':
        video = trail[0]['video']

    # Get image
    if 'images' in trail[0] and trail[0]['images']:
        # TODO: stich images
        image = trail[0]['images'][0]
    else:
        image = _post['blog']['avatar'][0]['url']

    reblog = {"by": '', "from": ''}
    try:
        reblog['from'] = post['reblogged_from_name']
        reblog['by'] = post['blog_name']
    except KeyError as e:
        pass

    description = ''
    if False and trail[0]['type'] == 'video':
        # truncate description; turns out discord doesn't need this, but other platforms might. todo
        _desc = trail[0]['content']
        if '\n' in _desc or len(_desc) > 48 or len(trail) > 1:
            description = trail[0]['blogname'] + ': ' + \
                    _desc.split('\n')[0][:48] + '... (see full post/thread)'
        else:
            description = trail[0]['blogname'] + ': ' + _desc
    else:
        n = 0
        for info in trail:
            description += f'\n\n{info["blogname"]}:\n\n'
            if n == 0 and title:
                description += f'# {title}\n\n'
            description += info['content']
            n += 1
    if description is not None:
        description = description.lstrip().rstrip()
    else:
        description = ''

    if reblog['from']:
        header = reblog["from"] + "🔁" + reblog["by"]
    else:
        header = trail[-1]["blogname"]

    return render_template('card.html',
            image = image,
            posturl = post['post_url'],
            header = header,
            op = trail[-1]['blogname'],
            video = video,
            desc = description,
            notes = post['note_count'],
            app_name=APP_NAME,
            base_url=BASE_URL
        )


@app.route('/oembed.json')
def oembed_json():
    out = {
        "type":request.args.get("ttype", None),
        "version":"1.0",
        "provider_name":"fxtumblr",
        "provider_url":"https://github.com/knuxify/",
        "title": request.args.get("op", None),
        "author_name":request.args.get("desc", None),
        "author_url":request.args.get("link", None)
    }

    return out


@app.route('/')
def redirect_to_repo():
    return redirect('https://github.com/knuxify/fxtumblr')
