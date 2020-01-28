import os
from web import app, moviedb, tvdb
from flasktools import fetch_image, strip_unicode_characters
from flasktools.celery import setup_celery
from flasktools.db import fetch_query, mutate_query

celery = setup_celery(app)


@celery.task(queue='scheduler')
def fetch_episode_image(tvdb_id: int):
	filename = tvdb.episode_image_filename(tvdb_id)
	if not os.path.exists(filename):
		print(f'Fetching episode {tvdb_id} image')
		try:
			remote = tvdb._send_request(f'/episodes/{tvdb_id}')['data']['filename']
		except tvdb.TVDBException as e:
			print(e)
			return None
		if remote:
			url = f'http://thetvdb.com/banners/{remote}'
			fetch_image(filename, url)


@celery.task(queue='scheduler')
def resync_tvshow(airdate: str, tvshow: dict, tvdb_token: str) -> None:
	name = tvshow['name']
	print(f'Checking date {airdate} for {name}')
	resp = tvdb.episode_search(tvshow['tvdb_id'], airdate, token=tvdb_token)
	if resp:
		print(f'Found for {name}')
		for r in resp:
			tvdb_id = r['id']
			season = r['airedSeason']
			episode = r['airedEpisodeNumber']
			if r['episodeName'] is None:
				r['episodeName'] = f'Season {season} Episode {episode}'
			r['episodeName'] = strip_unicode_characters(r['episodeName'])

			existing = fetch_query(
				"""
				SELECT
					*,
					(airdate - '1 day'::INTERVAL)::DATE::TEXT AS airdate
				FROM episode
				WHERE tvdb_id = %s
				""",
				(r['id'],),
				single_row=True
			)
			if not existing:
				# add 1 day to account for US airdates compared to NZ airdates
				mutate_query(
					"""
					INSERT INTO episode (
						tvshowid, seasonnumber, episodenumber, name, airdate, tvdb_id
					) VALUES (
						%s, %s, %s, %s, (%s::DATE + '1 day'::INTERVAL), %s
					) RETURNING id
					""",
					(
						tvshow['id'],
						season,
						episode,
						strip_unicode_characters(r['episodeName']),
						r['firstAired'],
						tvdb_id,
					)
				)
			else:
				print(f'{name} episode {tvdb_id} is not new')
				prevname = existing['name']
				# I didn't like the long if statement
				checkfor = [
					{'local': prevname, 'remote': r['episodeName']},
					{'local': existing['airdate'], 'remote':r['firstAired']},
					{'local': existing['seasonnumber'], 'remote':season},
					{'local': existing['episodenumber'], 'remote':episode}
				]
				changed = False
				for c in checkfor:
					if str(c['local']) != str(c['remote']):
						changed = True
				if changed:
					print(f'{name} episode {prevname} has changed')
					mutate_query(
						"""
						UPDATE episode SET
							name = %s,
							airdate = (%s::DATE + '1 day'::INTERVAL),
							seasonnumber = %s,
							episodenumber = %s
						WHERE id = %s
						""",
						(
							strip_unicode_characters(r['episodeName']),
							r['firstAired'],
							season,
							episode,
							existing['id'],
						)
					)


@celery.task(queue='scheduler')
def resync_movie(movie: dict) -> None:
	name = movie['name']
	releasedate = movie['releasedate']

	print(f'Resyncing {name}')
	resp = moviedb.get(movie['moviedb_id'])
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
