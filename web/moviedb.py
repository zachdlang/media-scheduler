# Standard library imports
import requests
import json
import os

# Third party imports
from flask import url_for, current_app as app

# Local imports
from sitetools.utility import (
	get_static_file, fetch_image
)


class MovieDBException(Exception):
	pass


def send_request(url, params):
	params['api_key'] = config.MOVIEDB_APIKEY
	r = requests.get(url, params=params).text
	resp = json.loads(r)
	return resp


def search(name):
	params = {'query': name}
	resp = send_request('https://api.themoviedb.org/3/search/movie', params)
	return resp['results']


def get(movie_moviedb_id):
	params = {}
	resp = send_request('https://api.themoviedb.org/3/movie/%s' % movie_moviedb_id, params)
	return resp


def image_search(movie_moviedb_id):
	resp = get(movie_moviedb_id)
	params = {}
	conf = send_request('https://api.themoviedb.org/3/configuration', params)
	size = None
	for s in conf['images']['poster_sizes']:
		if size is None and 'w' in s and int(s.replace('w', '')) >= 500:
			size = s
	resp['base_url'] = conf['images']['base_url']
	resp['poster_size'] = size
	return resp


def get_poster(moviedb_id):
	filename = get_static_file('/images/movie_poster_%s.jpg' % moviedb_id)
	if not os.path.exists(filename):
		resp = image_search(moviedb_id)
		poster_path = resp['poster_path']
		if poster_path:
			url = '%s%s%s' % (resp['base_url'], resp['poster_size'], resp['poster_path'])
			fetch_image(filename, url)
		else:
			return None
	return url_for('static', filename='images/movie_poster_%s.jpg' % moviedb_id)
