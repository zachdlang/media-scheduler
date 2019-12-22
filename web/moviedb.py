# Standard library imports
import requests
import json
import os

# Third party imports
from flask import url_for, Response

# Local imports
from web import config
from flasktools import get_static_file, fetch_image


class MovieDBException(Exception):
	pass


def _send_request(endpoint: str, params: dict) -> any:
	params['api_key'] = config.MOVIEDB_APIKEY
	r = requests.get(
		'https://api.themoviedb.org/3{}'.format(endpoint),
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
	resp = _send_request('/movie/{}'.format(movie_moviedb_id), params)
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
	filename = get_static_file('/images/movie_poster_{}.jpg'.format(moviedb_id))
	if not os.path.exists(filename):
		resp = image_search(moviedb_id)
		poster_path = resp['poster_path']
		if poster_path:
			url = '{}{}{}'.format(
				resp['base_url'], resp['poster_size'], resp['poster_path']
			)
			fetch_image(filename, url)
		else:
			return None
	return url_for(
		'static',
		filename='images/movie_poster_{}.jpg'.format(moviedb_id)
	)
