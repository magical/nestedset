drop table if exists posts;
create table posts
    ( id integer primary key
    , parent_post_id integer references posts (id)
    , left integer not null
    , right integer not null

    , body text not null
    , author text
    , post_time timestamp
    );
