# Standard library imports
import requests
import json
import os
from operator import itemgetter

# Third party imports
from flask import Response

# Local imports
from web import config
from flasktools import get_static_file, fetch_image, serve_static_file

MOVIE = 'movie'
TVSHOW = 'tv'


class MovieDBException(Exception):
	pass


def _request(endpoint: str, params: dict = None) -> any:
	params = params or {}
	params['api_key'] = config.MOVIEDB_APIKEY
	r = requests.get(
		f'https://api.themoviedb.org/3{endpoint}',
		params=params
	)
	try:
		r.raise_for_status()
	except requests.exceptions.HTTPError as e:
		raise MovieDBException from e
	resp = json.loads(r.text)
	return resp


def _parse_tvshow(item):
	"""
	Make sure expected keys exist, and figure out country.
	"""
	item['first_air_date'] = item.get('first_air_date')
	item['country'] = None
	if len(item['origin_country']) > 0:
		# Use first country of origin
		item['country'] = item['origin_country'][0]
	del item['origin_country']
	return item


def _search(category: str, name: str) -> list:
	params = {'query': name}
	resp = _request(f'/search/{category}', params)
	return resp['results']


def search_movies(name: str) -> list:
	return _search(MOVIE, name)


def search_tvshows(name: str) -> list:
	resp = _search(TVSHOW, name)
	return [_parse_tvshow(r) for r in resp]


def _get(category: str, moviedb_id: int) -> dict:
	resp = _request(f'/{category}/{moviedb_id}')
	return resp


def get_movie(moviedb_id: int) -> dict:
	return _get(MOVIE, moviedb_id)


def get_tvshow(moviedb_id: int) -> dict:
	resp = _get(TVSHOW, moviedb_id)
	return _parse_tvshow(resp)


def get_tvshow_season(moviedb_id: int, season_number: int) -> dict:
	resp = _request(f'/{TVSHOW}/{moviedb_id}/season/{season_number}')
	return resp


def _fetch_image(category: str, path: str, filename: str) -> dict:
	conf = _request('/configuration')

	size = None
	base_url = conf['images']['base_url']
	for s in conf['images'][f'{category}_sizes']:
		if s == 'original':
			size = 'original'

	if size is None:
		for s in conf['images'][f'{category}_sizes']:
			if 'w' in s:
				# Find largest available size
				curr_width = int(size.replace('w', '')) if size is not None else 0
				width = int(s.replace('w', ''))
				if width > curr_width:
					size = s

	if size is not None:
		url = f'{base_url}{size}{path}'
		print(url)
		fetch_image(filename, url)


def _fetch_poster(path, filename):
	_fetch_image('poster', path, filename)


def _fetch_still(path, filename):
	_fetch_image('still', path, filename)


def get_movie_poster(moviedb_id: int) -> Response:
	filename = get_static_file(f'/img/upload/movie_poster_{moviedb_id}.jpg')
	if not os.path.exists(filename):
		movie = get_movie(moviedb_id)
		_fetch_poster(movie['poster_path'], filename)

	return serve_static_file(
		f'img/upload/movie_poster_{moviedb_id}.jpg'
	)


def get_tvshow_poster(moviedb_id: int) -> Response:
	filename = get_static_file(f'/img/upload/tvshow_poster_{moviedb_id}.jpg')
	if not os.path.exists(filename):
		tvshow = get_tvshow(moviedb_id)
		_fetch_poster(tvshow['poster_path'], filename)

	return serve_static_file(
		f'img/upload/tvshow_poster_{moviedb_id}.jpg'
	)


def _episode_filename(moviedb_id: int, season: int, episode: int) -> str:
	return f'img/upload/episode_{moviedb_id}_{season}_{episode}.jpg'


def get_episode_static(moviedb_id: int, season: int, episode: int) -> Response:
	return serve_static_file(
		_episode_filename(moviedb_id, season, episode)
	)


def get_episode_image(moviedb_id: int, season: int, episode: int) -> Response:
	filename = get_static_file(
		f'/{_episode_filename(moviedb_id, season, episode)}'
	)
	if not os.path.exists(filename):
		try:
			resp = _request(
				f'/{TVSHOW}/{moviedb_id}/season/{season}/episode/{episode}/images'
			)
			if len(resp['stills']) > 0:
				# Find the highest rated image
				r = sorted(resp['stills'], key=itemgetter('vote_average'), reverse=True)[0]
				_fetch_still(r['file_path'], filename)
		except MovieDBException:
			print('Could not find any episode images')
