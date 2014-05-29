#!/usr/bin/env python2
# encoding=utf-8

from __future__ import unicode_literals

import os
import codecs

from flask import Flask, request, make_response, render_template, send_file
from flask.ext.autoindex import AutoIndex

import pygments
import pygments.lexers
import pygments.lexers.special
import pygments.formatters
import pygments.styles

import markdown2
from docutils.core import publish_string as rst_publish_string
from textile import textile
from mediawiki import wiki2html


app = Flask(__name__)
HOME = os.environ['HOME']
_REPO_DIR = os.environ.get('DOCUMENT_BASE', os.path.join(HOME, '.local', 'docs'))
autoindex = AutoIndex(app, _REPO_DIR, add_url_rules=False)

default_encoding = 'utf-8'

pygments_style = pygments.styles.get_style_by_name('borland')
pygments_html_formatter = pygments.formatters.HtmlFormatter(linenos=True, full=True, style=pygments_style)

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
    return rst_publish_string(source=content, writer_name='html4css1')

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


static_file_exts = [
    '.html',
    '.css',
    '.js',
]


def is_static_file(path):
    for ext in static_file_exts:
        if path.lower().endswith(ext):
            return True
    return False


def render_doc(content, render_func):
    article = render_func(content)
    if type(article) == str:
        article = article.decode('utf-8')
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

    content = read_file(abspath)
    is_static = is_static_file(abspath)

    doc_render_func = get_doc_render_func(abspath)
    pygments_lexer = get_pygments_lexer(abspath, encoding=default_encoding)

    should_render_raw = 'raw' in request.args
    is_unicode = type(content) == unicode

    if not pygments_lexer and is_unicode:
        pygments_lexer = pygments.lexers.special.TextLexer(encoding=default_encoding)

    if not is_unicode or is_static:
        should_render_raw = True

    if should_render_raw:
        return send_file(abspath)
    elif doc_render_func is not None:
        return render_doc(content, doc_render_func)
    elif pygments_lexer is not None:
        return render_source(content, pygments_lexer)
    else:
        send_file(abspath)

if __name__ == '__main__':
    import sys
    port = 8100
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port, debug=True, use_debugger=True)

