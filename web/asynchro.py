from web import app, moviedb
from flasktools.celery import setup_celery
from flasktools.db import fetch_query, mutate_query

celery = setup_celery(app)


def lpad(n, length=2):
	return str(n).zfill(length)


def format_episode(season, episode):
	return f"S{lpad(season)}E{lpad(episode)}"


def _populate_tvshow_episode(tvshow, season, episode):
	existing = fetch_query(
		"""
		SELECT *
		FROM episode
		WHERE moviedb_id = %s
		""",
		(episode['id'],),
		single_row=True
	)

	if not existing:
		episodename = format_episode(season, episode['episode_number'])
		print(f"Inserting {tvshow['name']} {episodename}")
		mutate_query(
			"""
			INSERT INTO episode (
				tvshowid, seasonnumber, episodenumber, name, airdate, moviedb_id
			) VALUES (
				%s, %s, %s, %s, %s, %s
			) RETURNING id
			""",
			(
				tvshow['id'],
				season,
				episode['episode_number'],
				episode['name'],
				episode['air_date'],
				episode['id'],
			)
		)


@celery.task(queue='scheduler')
def resync_tvshow(tvshow: dict) -> None:
	name = tvshow['name']

	print(f'Resyncing {name}')
	resp = moviedb.get_tvshow(tvshow['moviedb_id'])

	for s in resp['seasons']:
		s_resp = moviedb.get_tvshow_season(
			tvshow['moviedb_id'],
			s['season_number']
		)
		for e in s_resp['episodes']:
			season = s['season_number']
			if e['air_date'] is None:
				print(f"{format_episode(season, e['episode_number'])} has no air date")
				continue

			_populate_tvshow_episode(tvshow, season, e)


@celery.task(queue='scheduler')
def resync_movie(movie: dict) -> None:
	name = movie['name']
	releasedate = movie['releasedate']

	print(f'Resyncing {name}')
	resp = moviedb.get_movie(movie['moviedb_id'])
	changed = False
	newname = resp['title']
	newreleasedate = resp['release_date']

	if name != newname:
		changed = True
	if releasedate is not None:
		if releasedate != newreleasedate:
			changed = True

	if changed:
		print(f'"{name}" ({releasedate}) changed to "{newname}" ({newreleasedate})')
		mutate_query(
			"UPDATE movie SET name = %s, releasedate = %s WHERE id = %s",
			(newname, newreleasedate, movie['id'],)
		)
