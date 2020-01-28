# Standard library imports
import requests
import json
import os

# Third party imports
from flask import Response

# Local imports
from web import config
from flasktools import get_static_file, fetch_image, serve_static_file


class MovieDBException(Exception):
	pass


def _send_request(endpoint: str, params: dict) -> any:
	params['api_key'] = config.MOVIEDB_APIKEY
	r = requests.get(
		f'https://api.themoviedb.org/3{endpoint}',
		params=params
	).text
	resp = json.loads(r)
	return resp


def search(name: str) -> list:
	params = {'query': name}
	resp = _send_request('/search/movie', params)
	return resp['results']


def get(movie_moviedb_id: int) -> dict:
	params = {}
	resp = _send_request(f'/movie/{movie_moviedb_id}', params)
	return resp


def image_search(movie_moviedb_id: int) -> dict:
	resp = get(movie_moviedb_id)
	params = {}
	conf = _send_request('/configuration', params)
	size = None
	for s in conf['images']['poster_sizes']:
		if size is None and 'w' in s and int(s.replace('w', '')) >= 500:
			size = s
	resp['base_url'] = conf['images']['base_url']
	resp['poster_size'] = size
	return resp


def get_poster(moviedb_id: int) -> Response:
	filename = get_static_file(f'/img/upload/movie_poster_{moviedb_id}.jpg')
	if not os.path.exists(filename):
		resp = image_search(moviedb_id)
		base_url = resp['base_url']
		poster_size = resp['poster_size']
		poster_path = resp['poster_path']
		if poster_path:
			url = f'{base_url}{poster_size}{poster_path}'
			fetch_image(filename, url)
		else:
			return None
	return serve_static_file(
		f'img/upload/movie_poster_{moviedb_id}.jpg'
	)
