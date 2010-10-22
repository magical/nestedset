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
    return sqlite3.connect(app.config['DATABASE'])

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
        posts = query('select * from posts where left = (select max(left) as left from posts)')
        if not posts:
            left = 1
        else:
            assert len(posts == 1)
            post = posts[0]
            left = post['right'] + 1

    right = left + 1

    with g.db:
        cur = g.db.execute('update posts set left=left+2 where left > ?', [left])
        updated_left = cur.rowcount
        cur = g.db.execute('update posts set right=right+2 where right >= ?', [left])
        updated_right = cur.rowcount
        cur = g.db.execute('insert into posts (body, author, post_time, left, right, parent_post_id) values (?, ?, ?, ?, ?, ?)', [body, author, timestamp, left, right, parent_id])
        post_id = cur.lastrowid

    return post_id


@app.route('/', methods=('GET', 'POST'))
def thread():
    if request.method == 'GET':
        posts = query('select * from posts');
        return render_template('thread.html', posts=posts)
    elif request.method == 'POST':
        body = request.form['body'].decode('utf-8')
        author = request.form['author'].decode('utf-8')

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

        body = request.form['body'].decode('utf-8')
        author = request.form['author'].decode('utf-8')
            
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
    

