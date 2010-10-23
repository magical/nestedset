A proof-of-concept implementation of the [nested set][] model for storing threaded conversations.

There is no authentication, and only one top-level thread (or is there?).

Requires [Flask][] and Python 2.5 or better.

To run the app:

    % sqlite3 db.sqlite < schema.sql
    % python nestedset.py

[nested set]: http://en.wikipedia.org/wiki/Nested_set_model
[Flask]: http://flask.pocoo.org/
