#!/usr/bin/env python3

# The MIT License (MIT)
#
# Copyright (c) 2018-2022 Sunaina Pai
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


"""Make static website/blog with Python."""


import os
import shutil
import re
import glob
import sys
import json
import datetime
import markdown
from urllib.parse import urlsplit

def fread(filename):
    """Read file and close the file."""
    with open(filename, 'r', encoding="utf-8") as file:
        return file.read()


def fwrite(filename, text):
    """Write content to file and close the file."""
    basedir = os.path.dirname(filename)
    if not os.path.isdir(basedir):
        os.makedirs(basedir)

    with open(filename, 'w', encoding="utf-8") as file:
        file.write(text)


def log(msg, *args):
    """Log message with specified arguments."""
    sys.stderr.write(msg.format(*args) + '\n')


def truncate(text, words=25):
    """Remove tags and truncate text to the specified number of words."""
    return ' '.join(re.sub('(?s)<.*?>', ' ', text).split()[:words])


def read_headers(text):
    """Parse headers in text and yield (key, value, end-index) tuples."""
    for match in re.finditer(r'\s*<!--\s*(.+?)\s*:\s*(.+?)\s*-->\s*|.+', text):
        if not match.group(1):
            break
        yield match.group(1), match.group(2), match.end()


def rfc_2822_format(date_str):
    """Convert yyyy-mm-dd date string to RFC 2822 format date string."""
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    return date.strftime('%a, %d %b %Y %H:%M:%S +0000')


def read_content(filename):
    """Read content and metadata from file into a dictionary."""
    # Read file content.
    text = fread(filename)

    # Read metadata and save it in a dictionary.
    date_slug = os.path.basename(filename).split('.')[0]
    match = re.search(r'^(?:(\d\d\d\d-\d\d-\d\d)-)?(.+)$', date_slug)
    content = {
        'date': match.group(1) or '1970-01-01',
        'slug': match.group(2),
    }

    # Read headers.
    end = 0
    for key, val, end in read_headers(text):
        content[key] = val

    # Separate content from headers.
    text = text[end:]

    # Convert Markdown content to HTML.
    if filename.endswith(('.md', '.mkd', '.mkdn', '.mdown', '.markdown')):
        try:
            if _TEST == 'ImportError':
                raise ImportError('Error forced by test')
            text = markdown.markdown(text, extensions=['tables']) + '\n'
        except ImportError as err:
            log('WARNING: Cannot render Markdown in {}: {}', filename, str(err))

    # Update the dictionary with content and RFC 2822 date.
    content.update({
        'content': text,
        'rfc_2822_date': rfc_2822_format(content['date'])
    })

    return content


def render(template, **params):
    """Replace placeholders in template with values from params."""
    return re.sub(r'{{\s*([^}\s]+)\s*}}',
                  lambda match: str(params.get(match.group(1), match.group(0))),
                  template)


def make_pages(src, dst, layout, **params):
    """Generate pages from page content."""
    items = []

    for src_path in glob.glob(src):
        content = read_content(src_path)

        page_params = dict(params, **content)

        # Populate placeholders in content if content-rendering is enabled.
        if page_params.get('render') == 'yes':
            rendered_content = render(page_params['content'], **page_params)
            page_params['content'] = rendered_content
            content['content'] = rendered_content

        items.append(content)

        dst_path = render(dst, **page_params)
        output = render(layout, **page_params)

        log('Rendering {} => {} ...', src_path, dst_path)
        fwrite(dst_path, output)

    return sorted(items, key=lambda x: x['date'], reverse=True)


def make_list(posts, dst, list_layout, item_layout, **params):
    """Generate list page for a blog."""
    items = []
    for post in posts:
        item_params = dict(params, **post)
        item_params['summary'] = truncate(post['content'])
        item = render(item_layout, **item_params)
        items.append(item)

    params['content'] = ''.join(items)
    dst_path = render(dst, **params)
    output = render(list_layout, **params)

    log('Rendering list => {} ...', dst_path)
    fwrite(dst_path, output)


def main():
    # Default parameters.
    params = {
        'subtitle': 'Lorem Ipsum',
        'author': 'pwNd',
        'site_url': 'http://localhost:8000',
        'current_year': datetime.datetime.now().year,
        'site_dir': '_site',
        'static_dir': 'static',
        'content_dir': 'content',
        'layout_dir': 'layout',
        'blog_slug': 'blog',
        'news_slug': 'news'
    }

    # If params.json exists, load it.
    if os.path.isfile('params.json'):
        params.update(json.loads(fread('params.json')))

    # Keep config simple: allow using only site_url.
    # If base_path is omitted, derive it from site_url path (e.g. /my-site).
    if ('base_path' not in params or params['base_path'] == '') and params.get('site_url'):
        base_path = urlsplit(params['site_url']).path.rstrip('/')
        params['base_path'] = base_path

    # Backward-compatible fallback: if site_url is missing, build it from base_path.
    if not params.get('site_url'):
        params['site_url'] = 'http://localhost:8000' + params.get('base_path', '')

    site_dir = params['site_dir']
    static_dir = params['static_dir']
    content_dir = params['content_dir']
    layout_dir = params['layout_dir']
    blog_slug = params['blog_slug']
    news_slug = params['news_slug']
    
    # Create a new _site directory from scratch
    if os.path.isdir(site_dir):
        shutil.rmtree(site_dir)
    shutil.copytree(static_dir, site_dir)

    # Load layouts.
    page_layout = fread(os.path.join(layout_dir, 'page.html'))
    post_layout = fread(os.path.join(layout_dir, 'post.html'))
    list_layout = fread(os.path.join(layout_dir, 'list.html'))
    item_layout = fread(os.path.join(layout_dir, 'item.html'))
    feed_xml = fread(os.path.join(layout_dir, 'feed.xml'))
    item_xml = fread(os.path.join(layout_dir, 'item.xml'))

    # Combine layouts to form final layouts.
    post_layout = render(page_layout, content=post_layout)
    list_layout = render(page_layout, content=list_layout)

    # Create site pages.
    make_pages(os.path.join(content_dir, '_index.html'), os.path.join(site_dir, 'index.html'),
               page_layout, **params)
    make_pages(os.path.join(content_dir, '[!_]*.html'), os.path.join(site_dir, '{{ slug }}', 'index.html'),
               page_layout, **params)

    # Create blogs.
    blog_posts = make_pages(os.path.join(content_dir, blog_slug, '*.md'),
                            os.path.join(site_dir, blog_slug, '{{ slug }}', 'index.html'),
                            post_layout, blog=blog_slug, **params)
    news_posts = make_pages(os.path.join(content_dir, news_slug, '*.html'),
                            os.path.join(site_dir, news_slug, '{{ slug }}', 'index.html'),
                            post_layout, blog=news_slug, **params)

    # Create blog list pages.
    make_list(blog_posts, os.path.join(site_dir, blog_slug, 'index.html'),
              list_layout, item_layout, blog=blog_slug, title='Blog', **params)
    make_list(news_posts, os.path.join(site_dir, news_slug, 'index.html'),
              list_layout, item_layout, blog=news_slug, title='News', **params)

    # Create RSS feeds.
    make_list(blog_posts, os.path.join(site_dir, blog_slug, 'rss.xml'),
              feed_xml, item_xml, blog=blog_slug, title='Blog', **params)
    make_list(news_posts, os.path.join(site_dir, news_slug, 'rss.xml'),
              feed_xml, item_xml, blog=news_slug, title='News', **params)


# Test parameter to be set temporarily by unit tests.
_TEST = None


if __name__ == '__main__':
    main()
