
CREATE TABLE IF NOT EXISTS tvshow (
	id SERIAL primary key,
	name TEXT NOT NULL,
	tvdb_id INTEGER NOT NULL
)WITH OIDS;

CREATE TABLE IF NOT EXISTS episode (
	id SERIAL primary key,
	tvshowid INTEGER NOT NULL REFERENCES tvshow(id),
	seasonnumber INTEGER NOT NULL,
	episodenumber INTEGER NOT NULL,
	name TEXT NOT NULL,
	airdate DATE NOT NULL,
	tvdb_id INTEGER NOT NULL
)WITH OIDS;

CREATE TABLE IF NOT EXISTS watcher (
	id SERIAL primary key,
	firstname TEXT NOT NULL,
	surname TEXT NOT NULL,
	email TEXT NOT NULL,
	username TEXT NOT NULL,
	password TEXT NOT NULL,
	ipaddr INET
)WITH OIDS;

CREATE TABLE IF NOT EXISTS watcher_tvshow (
	id SERIAL primary key,
	tvshowid INTEGER NOT NULL REFERENCES tvshow(id),
	watcherid INTEGER NOT NULL REFERENCES watcher(id)
)WITH OIDS;

CREATE TABLE IF NOT EXISTS watcher_episode (
	id SERIAL primary key,
	episodeid INTEGER NOT NULL REFERENCES episode(id),
	watcherid INTEGER NOT NULL REFERENCES watcher(id),
	watched BOOLEAN NOT NULL DEFAULT FALSE
)WITH OIDS; 
