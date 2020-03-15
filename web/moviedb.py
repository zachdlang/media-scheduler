# Standard library imports
import requests
import json
import os

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
	).text
	resp = json.loads(r)
	return resp


def _search(category: str, name: str) -> list:
	params = {'query': name}
	resp = _request(f'/search/{category}', params)
	return resp['results']


def search_movies(name: str) -> list:
	return _search(MOVIE, name)


def search_tvshows(name: str) -> list:
	return _search(TVSHOW, name)


def _get(category: str, moviedb_id: int) -> dict:
	resp = _request(f'/{category}/{moviedb_id}')
	return resp


def get_movie(moviedb_id: int) -> dict:
	return _get(MOVIE, moviedb_id)


def get_tvshow(moviedb_id: int) -> dict:
	return _get(TVSHOW, moviedb_id)


def get_tvshow_season(moviedb_id: int, season_number: int) -> dict:
	resp = _request(f'/{TVSHOW}/{moviedb_id}/season/{season_number}')
	return resp


def image_search(item: dict) -> dict:
	conf = _request('/configuration')
	size = None
	for s in conf['images']['poster_sizes']:
		if size is None and 'w' in s and int(s.replace('w', '')) >= 500:
			size = s
	item['base_url'] = conf['images']['base_url']
	item['poster_size'] = size
	return item


def _fetch_poster(item, filename):
	resp = image_search(item)
	base_url = resp['base_url']
	poster_size = resp['poster_size']
	poster_path = resp['poster_path']
	if poster_path:
		url = f'{base_url}{poster_size}{poster_path}'
		fetch_image(filename, url)


def get_movie_poster(moviedb_id: int) -> Response:
	filename = get_static_file(f'/img/upload/movie_poster_{moviedb_id}.jpg')
	if not os.path.exists(filename):
		movie = get_movie(moviedb_id)
		_fetch_poster(movie, filename)

	return serve_static_file(
		f'img/upload/movie_poster_{moviedb_id}.jpg'
	)


def get_tvshow_poster(moviedb_id: int) -> Response:
	filename = get_static_file(f'/img/upload/tvshow_poster_{moviedb_id}.jpg')
	if not os.path.exists(filename):
		tvshow = get_tvshow(moviedb_id)
		_fetch_poster(tvshow, filename)

	return serve_static_file(
		f'img/upload/tvshow_poster_{moviedb_id}.jpg'
	)
