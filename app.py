#!/usr/bin/env python
# encoding=utf-8

import os
import codecs
import zipfile
import mimetypes
from datetime import datetime, timedelta

from flask import Flask, request, make_response, render_template, send_file, g, redirect, send_from_directory

import pygments
import pygments.lexers
import pygments.lexers.special
from pygments.formatters.html import HtmlFormatter as PygmentsHtmlFormatter
import pygments.styles

from docutils.core import publish_string as rst_publish_string, publish_parts as rst_publish_parts
from textile import textile
import markdown

app = Flask(__name__)
_REPO_DIR = os.path.abspath('./docs')

default_encoding = 'utf-8'

pygments_html_formatter = PygmentsHtmlFormatter(
    linenos=True,
    full=True,
    style=(pygments.styles.get_style_by_name('pastie')),
)


markdown_extensions = [
    'markdown.extensions.codehilite',
    'markdown.extensions.fenced_code',
    'markdown.extensions.footnotes',
    'markdown.extensions.smarty',
    'markdown.extensions.tables',
    'markdown.extensions.toc',
    'markdown.extensions.meta',
]


def render_markdown(content):
    return markdown.markdown(content, extensions=markdown_extensions)


def render_rst(content):
    # return rst_publish_string(source=content, writer_name='html5')
    a = rst_publish_parts(source=content, writer_name='html5')
    # print(a.keys())
    return a['body']


def render_textile(content):
    return textile(content, html_type='html')


# def render_mediawiki(content):
#     # return wiki2html(content, True)
#     result = mwparserfromhell.parser.Parser().parse(content)
#     return None


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
    # {
    #     'ext': ['mediawiki', 'wiki'],
    #     'render_func': render_mediawiki,
    # },
]


def get_ext(path):
    i = path.rfind('.')
    if i >= 0:
        return path[i+1:]


def get_basename(path):
    return os.path.basename(path)


def get_doc_render_func(path):
    for renderer in doc_renderers:
        if get_ext(path.lower()) in renderer['ext']:
            return renderer.get('render_func')


def get_pygments_lexer(path, **options):
    filename = get_basename(path)
    try:
        return pygments.lexers.get_lexer_for_filename(filename, **options)
    except pygments.util.ClassNotFound:
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
        return render_template('post.html', article=article)
    else:  # bytes
        return article


def render_source(content, lexer):
    return pygments.highlight(content, lexer, pygments_html_formatter)


def render_plain_text(content):
    resp = make_response(content)
    resp.content_type = 'text/plain'
    return resp


def render_md_slide(content):
    html = render_markdown(content)
    slides = filter(lambda x: not not x, html.split('<hr />'))
    return render_template("slide.html", slides=slides)


def render_dir(full_path, rel_path):
    files = sorted(os.listdir(full_path))
    return render_template('dir.html', rel_path=rel_path, files=[
        Path(os.path.join(full_path, f), rel_path)
        for f in files
    ])


def render_zipfile(full_path, rel_path, req_path):
    with zipfile.ZipFile(full_path) as f:
        if not rel_path:
            return render_template('dir.html', files=[
                ZipFilePath(req_path, zf)
                for zf in sorted(f.namelist())
                if not zf.endswith('/')
            ])
        else:
            with f.open(rel_path) as ff:
                content = ff.read()
            resp = make_response(content)
            mimetype = mimetypes.guess_type('http://example.org/%s' % rel_path)
            resp.mimetype = mimetype[0] or 'application/octet-stream'
            resp.expires = datetime.utcnow() + timedelta(seconds=100)
            return resp


class Path(object):
    def __init__(self, path, rel_path):
        self.path = path
        self.filename = os.path.basename(path)
        self.uri = os.path.join('/', rel_path, self.filename)
        self.is_dir = os.path.isdir(path)


class ZipFilePath(object):
    def __init__(self, basepath, filename):
        self.uri = '%s:/%s' % (basepath, filename)
        self.filename = filename
        self.is_dir = False


@app.route('/', defaults={'input_path': ''})
@app.route('/<path:input_path>')
def index(input_path):
    if ':/' in input_path:
        req_path, inner_path = input_path.split(':/', 1)
    else:
        req_path = input_path
        inner_path = None
    abspath = os.path.join(_REPO_DIR, req_path)
    if not os.path.exists(abspath):
        return '<h1>NOTHING TO SEE HERE</h1>', 404

    if os.path.isdir(abspath):
        return render_dir(abspath, req_path)

    should_render_zipfile = req_path.endswith('.jar')

    if should_render_zipfile:
        if not inner_path:
            return redirect('%s:/index.html' % req_path)
        return render_zipfile(abspath, inner_path, req_path)

    content = read_file(abspath)
    is_static = is_static_file(abspath)

    doc_render_func = get_doc_render_func(abspath)
    pygments_lexer = get_pygments_lexer(abspath, encoding=default_encoding)

    should_render_raw = 'raw' in request.args or 'r' in request.args
    is_unicode = type(content) == str

    should_render_source = ('source' in request.args or 'referer' not in request.headers) and (pygments_lexer is not None)

    is_slide = 'slide' in request.args

    if not pygments_lexer and is_unicode:
        pygments_lexer = pygments.lexers.special.TextLexer(encoding=default_encoding)

    if not should_render_source and (not is_unicode or is_static):
        should_render_raw = True

    setattr(g, 'math', 'math' in request.args)

    try:
        if is_slide:                return render_md_slide(content)
        elif should_render_raw:
            if is_static:           return send_file(abspath)
            elif pygments_lexer:    return render_source(content, pygments_lexer)
            elif is_unicode:        return render_plain_text(content)
            else:                   return send_file(abspath)
        elif doc_render_func:   return render_doc(content, doc_render_func)
        elif pygments_lexer:    return render_source(content, pygments_lexer)
        else:                   return send_file(abspath)
    except Exception:
        import traceback
        return render_plain_text(traceback.format_exc())


@app.route('/static/pygments.css')
def pygments_css():
    css_text = pygments_html_formatter.get_style_defs('.codehilite')
    resp = make_response(css_text)
    resp.mimetype = 'text/css'
    return resp


if __name__ == '__main__':
    import sys
    port = 8100
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    app.run(host='127.0.0.1', port=port, debug=True, use_debugger=True)

