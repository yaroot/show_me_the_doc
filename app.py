#!/usr/bin/env python2
# encoding=utf-8

from __future__ import unicode_literals

import os
import codecs

from flask import Flask, request, make_response, render_template, send_file
from flask.ext.autoindex import AutoIndex
from flask_bootstrap import Bootstrap

import pygments
import pygments.lexers
import pygments.lexers.special
import pygments.formatters
import pygments.styles

from docutils.core import publish_string as rst_publish_string
from textile import textile
from mediawiki import wiki2html
# import CommonMark
# import mistune
import markdown2

app = Flask(__name__)
Bootstrap(app)
_REPO_DIR = os.environ.get('DOCUMENT_BASE')
if not _REPO_DIR:
    HOME = os.environ['HOME']
    _REPO_DIR = os.path.join(HOME, '.local', 'docs')

autoindex = AutoIndex(app, _REPO_DIR, add_url_rules=False)

default_encoding = 'utf-8'

pygments_style = pygments.styles.get_style_by_name('github')
pygments_html_formatter = pygments.formatters.HtmlFormatter(linenos=True, full=True, style=pygments_style)

markdown_extensions = [
    'code-friendly',
    'fenced-code-blocks',
    'footnotes',
    'nofollow',
    'header-ids',
    'metadata',
    'toc',
    'tables',
    'wiki-tables',
]

# markdown_exts = [
#     hoep.EXT_AUTOLINK,
#     hoep.EXT_FENCED_CODE,
#     hoep.EXT_FOOTNOTES,
#     hoep.EXT_TABLES,
#     hoep.EXT_QUOTE,
#     hoep.EXT_UNDERLINE,
# ]


#def bxor_all(l):
#    return reduce(lambda a, b: a|b, l)

#markdown = hoep.Hoep(bxor_all(markdown_exts))
#markdown = hoep.Hoep(hoep.EXT_FENCED_CODE)
# markdown = hoedown.Markdown(hoedown.HtmlRenderer(reduce(lambda a, b: a | b, markdown_extensions)))


def render_markdown(content):
    # return markdown.render(content)
    # ast = CommonMark.DocParser().parse(content)
    # return CommonMark.HTMLRenderer().render(ast)
    # return mistune.markdown(content)
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


def get_doc_render_func(path):
    for renderer in doc_renderers:
        if get_ext(path.lower()) in renderer['ext']:
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


def render_plain_text(content):
    resp = make_response(content)
    resp.content_type = 'text/plain'
    return resp


@app.route('/', defaults={'path':'.'})
@app.route('/<path:path>')
def show_me_the_doc(path):
    abspath = os.path.join(_REPO_DIR, path)
    if not os.path.exists(abspath):
        return '<h1>NOTHING TO SEE HERE</h1>', 404

    if os.path.isdir(abspath):
        return autoindex.render_autoindex(path=path, endpoint='.show_me_the_doc')

    content = read_file(abspath)
    is_static = is_static_file(abspath)

    doc_render_func = get_doc_render_func(abspath)
    pygments_lexer = get_pygments_lexer(abspath, encoding=default_encoding)

    should_render_raw = 'raw' in request.args or 'r' in request.args
    is_unicode = type(content) == unicode

    if not pygments_lexer and is_unicode:
        pygments_lexer = pygments.lexers.special.TextLexer(encoding=default_encoding)

    if not is_unicode or is_static:
        should_render_raw = True

    if should_render_raw:
        if is_static:           return send_file(abspath)
        elif pygments_lexer:    return render_source(content, pygments_lexer)
        elif is_unicode:        return render_plain_text(content)
        else:                   return send_file(abspath)
    elif doc_render_func:   return render_doc(content, doc_render_func)
    elif pygments_lexer:    return render_source(content, pygments_lexer)
    else:                   return send_file(abspath)


@app.route('/_static/pygments.css')
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
    app.run(host='0.0.0.0', port=port, debug=True, use_debugger=True)

