
CREATE TABLE IF NOT EXISTS tvshow (
	id SERIAL primary key,
	name TEXT NOT NULL,
	tvdb_id INTEGER NOT NULL,
	adminid INTEGER NOT NULL REFERENCES admin(id)
)WITH OIDS;

CREATE TABLE IF NOT EXISTS episode (
	id SERIAL primary key,
	tvshowid INTEGER NOT NULL REFERENCES tvshow(id),
	seasonnumber INTEGER NOT NULL,
	episodenumber INTEGER NOT NULL,
	name TEXT NOT NULL,
	airdate DATE NOT NULL,
	tvdb_id INTEGER NOT NULL,
	watched BOOLEAN NOT NULL DEFAULT FALSE
)WITH OIDS;

CREATE TABLE IF NOT EXISTS admin (
	id SERIAL primary key,
	firstname TEXT NOT NULL,
	surname TEXT NOT NULL,
	email TEXT NOT NULL,
	username TEXT NOT NULL,
	password TEXT NOT NULL
)WITH OIDS;
