#!/usr/bin/env python2
# encoding=utf-8

from __future__ import unicode_literals

import os
import codecs

from flask import Flask, request, make_response, render_template
from flask.ext.autoindex import AutoIndex

import pygments
import pygments.lexers
import pygments.formatters
import pygments.styles

import markdown2
from docutils.core import publish_string
from textile import textile
from mediawiki import wiki2html

_REPO_DIR = os.environ.get('DOCUMENT_BASE', os.path.join(os.environ['HOME'], '.local', 'docs'))

app = Flask(__name__)
HOME = os.environ['HOME']
autoindex = AutoIndex(app, _REPO_DIR, add_url_rules=False)

default_encoding = 'utf-8'

pygments_style = pygments.styles.get_style_by_name('borland')
pygments_html_formatter = pygments.formatters.HtmlFormatter(filenos=True, full=True, style=pygments_style)

markdown_extensions = [
    'code-friendly',
    'fenced-code-blocks',
    'footnotes'
    'header-ids',
    'metadata',
    'nofollow',
    'smarty-pants',
    'toc',
    'wiki-tables',
]

def render_markdown(content):
    return markdown2.markdown(content, extras=markdown_extensions)

def render_rst(content):
    return publish_string(source=content, writer_name='html4css1')

def render_textile(content):
    return textile(content, html_type='html')

def render_mediawiki(content):
    return wiki2html(content, True)

doc_renderers = [
    {
        'ext': ['md', 'mkd', 'markdown'],
        'render_func': render_markdown,
    },
    {
        'ext': ['rst'],
        'render_func': render_rst,
    },
    {
        'ext': ['textile'],
        'render_func': render_textile,
    },
    {
        'ext': ['mediawiki', 'wiki'],
        'render_func': render_mediawiki,
    },
]


def get_ext(path):
    i = path.rfind('.')
    if i >= 0:
        return path[i+1:]


def get_basename(path):
    return os.path.basename(path)


def test_exts(path, exts):
    ext = get_ext(path)
    if ext is not None:
        for e in exts:
            if ext == e:
                return True
    return False


def get_doc_render_func(path):
    for renderer in doc_renderers:
        if test_exts(path.lower(), renderer['ext']):
            return renderer.get('render_func')


def get_pygments_lexer(path, **options):
    filename = get_basename(path)
    try:
        return pygments.lexers.get_lexer_for_filename(filename, **options)
    except pygments.util.ClassNotFound, e:
        pass


def read_file(fp):
    try:
        with codecs.open(fp, encoding=default_encoding) as f:
            return f.read()
    except:
        with open(fp, mode='rb') as f:
            return f.read()


mime_types = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'text/javascript',
}


def guess_mime_type(path):
    for ext, mime in mime_types.items():
        if path.lower().endswith(ext):
            return mime


def render_raw(content, mimetype):
    resp = make_response(content)
    if mimetype is not None:
        resp.mimetype = mimetype
    else:
        if type(content) == unicode:
            resp.mimetype = 'text/plain'
        else:
            resp.mimetype = ''
    return resp


def render_doc(content, render_func):
    article = render_func(content)
    return render_template('article.html', article=article)


def render_source(content, lexer):
    return pygments.highlight(content, lexer, pygments_html_formatter)


@app.route('/', defaults={'path':'.'})
@app.route('/<path:path>')
def show_me_the_doc(path):
    mdfile = path
    abspath = os.path.join(_REPO_DIR, mdfile)
    if not os.path.exists(abspath):
        return '<h1>NOTHING TO SEE HERE</h1>', 404

    if os.path.isdir(abspath):
        return autoindex.render_autoindex(path=mdfile, endpoint='.show_me_the_doc')

    raw = 'raw' in request.args
    content = read_file(abspath)
    mimetype = guess_mime_type(abspath)

    doc_render_func = get_doc_render_func(abspath)
    pygments_lexer = get_pygments_lexer(abspath, encoding=default_encoding)

    if raw:
        return render_raw(content, mimetype)
    elif doc_render_func is not None:
        return render_doc(content, doc_render_func)
    elif pygments_lexer is not None:
        return render_source(content, pygments_lexer)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8100, debug=True, use_debugger=True)

