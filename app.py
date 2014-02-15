#!/usr/bin/env python2
# encoding=utf-8

from __future__ import unicode_literals

import os
import codecs
from flask import Flask, request, make_response
from flask.ext.autoindex import AutoIndex
import markdown2

_REPO_DIR = os.path.join(os.environ['HOME'], 'repos')

app = Flask(__name__)
HOME = os.environ['HOME']
autoindex = AutoIndex(app, _REPO_DIR, add_url_rules=False)

md_exts = [
    'md',
    'mkd',
    'markdown',
]

def is_md_ext(path):
    path = path.lower()
    for ext in md_exts:
        if path.endswith('.%s' % ext):
            return True
    return False


def read_file(fp):
    with codecs.open(fp, encoding='utf-8') as f:
        return f.read()


@app.route('/', defaults={'path':'.'})
@app.route('/<path:path>')
def show_me_the_doc(path):
    mdfile = path
    path = os.path.join(_REPO_DIR, path)
    if os.path.exists(path):
        if os.path.isdir(path):
            return autoindex.render_autoindex(path=mdfile, endpoint='.show_me_the_doc')
        else:
            raw = 'raw' in request.args
            if raw or not is_md_ext(path):
                content = read_file(path)
                resp = make_response(content)
                resp.mimetype = 'text/plain'
                return resp
            else:
                content = read_file(path)
                rendered = markdown2.markdown(content)
                return rendered
    else:
        return '<h1>NOTHING TO SEE HERE</h1>', 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8100, debug=True, use_debugger=True)

