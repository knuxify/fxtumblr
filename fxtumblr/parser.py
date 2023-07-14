"""
Contains code for getting data from Tumblr's API and parsing it.
"""

from bs4 import BeautifulSoup
from markdownify import markdownify

from .config import config

async def get_trail(post: dict, post_body: str = '') -> dict:
    trail = []

    # Custom handling for audio-only posts (type == 'audio'):
    # since these are not included in the reblog trail, we have to add
    # a little placeholder
    if post['type'] == 'audio':
        info = {
            "type": "audio",
            "content": f"{post['track_name']} (1 audio file attached)",
            "content_html": f"{post['track_name']} (1 audio file attached)",
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
            "content_html": "(video)",
            "video": {
                "url": post['video_url'],
                "height": post['thumbnail_height'],
                "width": post['thumbnail_width'],
                "thumbnail": post['thumbnail_url']
            },
            "images": [post['thumbnail_url']]
        }
        if 'reblogged_root_name' in post:
            info['blogname'] = post['reblogged_root_name']
        else:
            info['blogname'] = post['blog']['name']
        trail.append(info)

    # Custom handling for photo-only posts (type == 'photo'):
    # since these are not included in the reblog trail, we have to add
    # a little placeholder
    if post['type'] == 'photo':
        info = {
            "type": "text",
            "content": "(images)",
            "images": [photo['original_size']['url'] for photo in post['photos']]
        }

        images_include = ''
        for image in info['images']:
            images_include += f'<p><figure class="tmblr-full"><img src="{image}"></figure></p>'
        info['content_html'] = images_include

        if 'reblogged_root_name' in post:
            info['blogname'] = post['reblogged_root_name']
        else:
            info['blogname'] = post['blog']['name']

        trail.append(info)

    skip_placeholders = False
    if len(trail) + len(post['trail']) == 1:
        skip_placeholders = True

    for p in post['trail']:
        trail.append(await get_post_info(p, skip_placeholders=skip_placeholders))

    # Workaround for bug where reblogged root user is ignored and the second
    # reblogger appears as the OP of the first post.
    if 'reblogged_root_name' in post:
        trail[0]['blogname'] = post['reblogged_root_name']

    # Custom handling for asks (type == 'answer'):
    # the question is not included in the main content, so we have to
    # prepend it manually
    if post['type'] == 'answer':
        trail[0]['content'] = f'{post["asking_name"]} asked:' + "\n" + markdownify(post['question']).strip() + f"\n\n{trail[0]['blogname']} answered:\n" + trail[0]['content']
        trail[0]['content_html'] = f'<div class="question"><p class="question-header"><strong class="asking-name">{post["asking_name"]}</strong> asked:</p>\n' + post['question'] + '</div>\n' + trail[0]['content_html']

    if len(trail) == 1:
        if trail[0]['type'] == ['video']:
            trail[0]['content'] = ''

    # Limit the amount of images in a thread to prevent DDoS with long posts
    n_images = 0
    n_post = 0
    for p in trail:
        soup = BeautifulSoup(p['content_html'], 'html.parser')
        for image in soup.findAll('img'):
            n_images += 1
            if n_images > config['max_images_in_thread']:
                image.replaceWith('(too many images - see original post) ')
        trail[n_post]['content_html'] = str(soup)
        n_post += 1

    return trail


async def get_post_info(post: dict, skip_placeholders: bool = False) -> dict:
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
                info['video']['thumbnail'] = info['video']['url']\
                    .replace('.mp4', '_frame1.jpg')\
                    .replace('va.media.tumblr.com', '64.media.tumblr.com')\
                    .replace('ve.media.tumblr.com', '64.media.tumblr.com')

                fig.replaceWith('')
        images = [info['video']['thumbnail']]

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
            # Embedded gifs with attribution are skipped in regular content but included in content_raw. Prepend them manually.
            if image['src'] not in info['content_html']:
                try:
                    info['content_html'] = f'<p><figure class="tmblr-full"><img src={image["src"]}></figure></p><p><span class="gif-attribution">GIF by {image.parent["data-tumblr-attribution"].split(":")[0]}</span></p>' + info['content_html']
                except KeyError:
                    info['content_html'] = f'<p><figure class="tmblr-full"><img src={image["src"]}></figure></p>' + info['content_html']
            if not skip_placeholders:
                image.replaceWith('(image) ')
            else:
                image.replaceWith('')

    info['images'] = images

    content_html = str(soup)
    info['content'] = markdownify(content_html).strip()
    if not info['content']:
        if info['type'] == 'video':
            info['content'] = '(video)'
        elif info['type'] == 'audio':
            info['content'] = '(audio)'

    return info
