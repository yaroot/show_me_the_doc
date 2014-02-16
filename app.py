#!/usr/bin/env python2
# encoding=utf-8

from __future__ import unicode_literals

import os
import codecs
from flask import Flask, request, make_response
from flask.ext.autoindex import AutoIndex
import markdown2
from docutils.core import publish_string

_REPO_DIR = os.path.join(os.environ['HOME'], 'repos')

app = Flask(__name__)
HOME = os.environ['HOME']
autoindex = AutoIndex(app, _REPO_DIR, add_url_rules=False)

def render_markdown(content):
    return markdown2.markdown(content)

def render_rst(content):
    return publish_string(source=content, writer_name='html4css1')

renderers = [
    {
        'ext': ['md', 'mkd', 'markdown'],
        'render_func': render_markdown,
    },
    {
        'ext': ['rst'],
        'render_func': render_rst,
    },
]

def test_exts(path, exts):
    for ext in exts:
        if path.endswith('.%s' % ext):
            return True
    return False

def get_render_func(path):
    renderer = None
    for r in renderers:
        if test_exts(path.lower(), r['ext']):
            renderer = r
            break
    if renderer is not None:
        render_func = renderer['render_func']
        return render_func
    return None

def read_file(fp):
    try:
        with codecs.open(fp, encoding='utf-8') as f:
            return f.read()
    except:
        with open(fp, mode='rb') as f:
            return f.read()


@app.route('/', defaults={'path':'.'})
@app.route('/<path:path>')
def show_me_the_doc(path):
    mdfile = path
    abspath = os.path.join(_REPO_DIR, mdfile)
    if os.path.exists(abspath):
        if os.path.isdir(abspath):
            return autoindex.render_autoindex(path=mdfile, endpoint='.show_me_the_doc')
        else:
            render_func = get_render_func(abspath)
            raw = 'raw' in request.args
            content = read_file(abspath)

            is_html = abspath.lower().endswith('.html')
            if is_html and not raw:
                return content
            elif raw or render_func is None:
                resp = make_response(content)
                if type(content) == unicode:
                    resp.mimetype = 'text/plain'
                else:
                    resp.mimetype = ''
                return resp
            else:
                rendered = render_func(content)
                return rendered
    else:
        return '<h1>NOTHING TO SEE HERE</h1>', 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8100, debug=True, use_debugger=True)

