import sqlite3
from datetime import datetime
from operator import itemgetter

from flask import Flask, request, session, url_for, abort, render_template, flash, g, redirect

DATABASE = 'db.sqlite'
DEBUG = True
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

    Returns a list of (node, children) pairs."""

    tree = []
    thing = Thing(nodes)
    while thing.cur:
        node = thing.cur
        thing.next()
        tree.append(_set_to_tree(thing, node))

    return tree

def _set_to_tree(thing, self):
    children = []
    while thing.cur and thing.cur['right'] < self['right']:
        node = thing.cur
        thing.next()
        children.append(_set_to_tree(thing, node))
    return self, children

class Thing:
    def __init__(self, seq):
        self.it = iter(seq)
        self.next()

    def next(self):
        try:
            self.cur = self.it.next()
        except StopIteration:
            self.cur = None

@app.route('/', methods=('GET', 'POST'))
def thread():
    if request.method == 'GET':
        posts = set_to_tree(query('select * from posts order by left'));
        return render_template('thread.html', posts=posts)
    elif request.method == 'POST':
        body = request.form['body']
        author = request.form['author']

        post_id = create_post(body, author)
        return redirect("/#p{0}".format(post_id))

@app.route('/reply/<int:post_id>', methods=('GET', 'POST'))
def reply(post_id):
    if request.method == 'GET':
        post = query_one('select * from posts where id=?', [post_id])
        parents = query('select * from posts where left <= ? order by left', [post['left']])
        return render_template('reply.html', parents=parents)
    elif request.method == 'POST':
        parent_id = post_id

        body = request.form['body']
        author = request.form['author']
            
        post_id = create_post(body, author, parent_id=parent_id)

        return redirect("/#p{0}".format(post_id))


@app.before_request
def _open_db():
    g.db = connect_db()

@app.after_request
def _close_db(response):
    g.db.close()
    return response

if __name__ == '__main__':
    app.run(port=5009)
    

