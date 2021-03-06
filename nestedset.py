# coding: utf-8

"""nestedset - A throwaway threaded discussion web app"""

# Copyright © 2010 Andrew Ekstedt

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import sqlite3
from datetime import datetime
from operator import itemgetter

from flask import Flask, request, abort, render_template, g, redirect

DATABASE = 'db.sqlite'
DEBUG = False
SECRET_KEY = 'uy+4rVq/YjkYPV5AlyMU97A0qUiECCALt11c6LJBgGI='

app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)

def query(*args, **kw):
    cur = g.db.execute(*args, **kw)
    columns = map(itemgetter(0), cur.description)
    rows = [dict(zip(columns, row)) for row in cur]
    return rows

def query_one(*args, **kw):
    rows = query(*args, **kw)
    if len(rows) == 0:
        abort(404)
    elif len(rows) == 1:
        return rows[0]
    abort(500)

def create_post(body, author=None, parent_id=None):
    timestamp = datetime.now()
    
    if parent_id is not None:
        parent = query_one('select * from posts where id=?', [parent_id])
        left = parent['right']
    else:
        rows = g.db.execute('select max(right) from posts;').fetchall()
        if not rows:
            left = 1
        else:
            assert len(rows) == 1
            max_right = rows[0][0]
            left = max_right + 1

    right = left + 1

    with g.db:
        cur = g.db.execute('update posts set left=left+2 where left > ?', [left])
        updated_left = cur.rowcount
        cur = g.db.execute('update posts set right=right+2 where right >= ?', [left])
        updated_right = cur.rowcount
        cur = g.db.execute('insert into posts (body, author, post_time, left, right, parent_post_id) values (?, ?, ?, ?, ?, ?)', [body, author, timestamp, left, right, parent_id])
        post_id = cur.lastrowid

    return post_id

def set_to_tree(nodes):
    """Transform a list of nested-set nodes into a tree.

    Assumes the nodes are already sorted by 'left'.
    Returns a list of (node, children) pairs."""

    thing = Thing(nodes)
    trees = []
    while thing.next:
        node = thing.advance()
        trees.append(_set_to_tree(thing, node))
    return trees

def _set_to_tree(thing, self):
    children = []
    while thing.next and thing.next['right'] < self['right']:
        node = thing.advance()
        children.append(_set_to_tree(thing, node))
    return self, children

class Thing:
    '''This is sort of a wrapper around an iterator with lookahead(1).
    The next element is available at thing.next, and thing.advance() returns
    thing.next and advances the iterator (setting thing.next to the next 
    element). If there are no more elements, thing.next is set to None.
    '''
    def __init__(self, seq):
        self.it = iter(seq)
        self.next = self.it.next()

    def advance(self):
        node = self.next
        try:
            self.next = self.it.next()
        except StopIteration:
            self.next = None
        return node

@app.route('/', methods=('GET', 'POST'))
def thread():
    if request.method == 'GET':
        posts = set_to_tree(query('select * from posts order by left'));
        return render_template('thread.html', posts=posts)
    elif request.method == 'POST':
        body = request.form['body'].strip()
        author = request.form['author'].strip() or None

        if not body:
            posts = set_to_tree(query('select * from posts order by left'))
            return render_template('thread.html', posts=posts, error='You must enter a post body.')

        post_id = create_post(body, author)
        return redirect("/#p{0}".format(post_id))

@app.route('/reply/<int:post_id>', methods=('GET', 'POST'))
def reply(post_id):
    if request.method == 'GET':
        post = query_one('select * from posts where id=?', [post_id])
        parents = query('select * from posts where left <= ? and ? <= right order by left', [post['left'], post['right']])
        return render_template('reply.html', parents=parents)
    elif request.method == 'POST':
        parent_id = post_id

        body = request.form['body'].strip()
        author = request.form['author'].strip() or None

        if not body:
            error = 'You must enter a post body'

            post = query_one('select * from posts where id=?', [post_id])
            parents = query('select * from posts where left <= ? and ? <= right order by left', [post['left'], post['right']])
            return render_template('reply.html', parents=parents, error=error)
            
        post_id = create_post(body, author, parent_id=parent_id)

        return redirect("/#p{0}".format(post_id))

PAGE_SIZE = 50

@app.route("/recent")
def recent():
    page = request.args.get('page', 1, type=int)
    if page < 1:
        abort(404)
    skip = 50 * (page - 1)
    posts = query('select * from posts order by post_time desc limit ? offset ?',
                  [PAGE_SIZE, skip])
    count = query_one('select count(*) as "count" from posts')['count']
    more = skip + PAGE_SIZE < count
    if not posts:
        abort(404)

    return render_template('recent.html', posts=posts, page=page, more=more)

@app.route("/recent/<int:post_id>")
def recent_subthread(post_id):
    post = query_one('select * from posts where id = ?', [post_id])

    page = request.args.get('page', 1, type=int)
    if page < 1:
        abort(404)
    skip = 50 * (page - 1)

    posts = query('select * from posts where ? <= left and right <= ? order by post_time desc limit ? offset ?',
                  [post['left'], post['right'], PAGE_SIZE, skip])
    if not posts:
        abort(404)

    count = query_one('select count(*) from posts where ? <= left and right <= ?',
                      [post['left'], post['right']])
    more = skip + PAGE_SIZE < count

    return render_template('recent.html', posts=posts, page=page, more=more)


@app.route("/subthread/<int:post_id>")
def subthread(post_id):
    post = query_one('select * from posts where id = ?', [post_id])
    parents = query('select * from posts where left < ? and ? < right order by left', [post['left'], post['right']])
    posts = query('select * from posts where ? <= left and right <= ? order by left', [post['left'], post['right']])
    posts = set_to_tree(posts)
    return render_template('subthread.html', parents=parents, posts=posts, post=post)

@app.before_request
def _open_db():
    g.db = connect_db()

@app.after_request
def _close_db(response):
    g.db.close()
    return response

if __name__ == '__main__':
    import sys
    if 1 < len(sys.argv) and sys.argv[1] == 'debug':
        app.config['DEBUG'] = True
        app.run(port=5009)
    else:
        app.run("0.0.0.0", port=5009)

