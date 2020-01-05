# Standard library imports
import os
import requests
import json

# Third party imports
from flask import Response

# Local imports
from web import celery, config
from flasktools import get_static_file, fetch_image, serve_static_file


class TVDBException(Exception):
	pass


def get_headers() -> dict:
	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
	}
	return headers


def login() -> str:
	data = {
		'apikey': config.TVDB_APIKEY
	}
	headers = get_headers()
	resp = requests.post(
		'https://api.thetvdb.com/login',
		data=json.dumps(data),
		headers=headers
	)
	if resp.status_code == 503:
		raise TVDBException('TVDB currently down. Please try again later.')
	resp = json.loads(resp.text)
	if 'Error' in resp:
		raise TVDBException(resp['Error'])
	return resp['token']


def _send_request(endpoint: str, params: dict = None, token: str = None) -> any:
	if token is None:
		token = login()
	headers = get_headers()
	headers['Authorization'] = 'Bearer {}'.format(token)
	r = requests.get(
		'https://api.thetvdb.com{}'.format(endpoint),
		params=params,
		headers=headers
	).text
	resp = json.loads(r)
	if 'Error' in resp:
		if resp['Error'].lower() == 'resource not found':
			# No search results
			resp['data'] = []
		else:
			raise TVDBException(resp['Error'])
	return resp


def series_search(name: str) -> list:
	params = {'name': name}
	resp = _send_request('/search/series', params)
	return resp['data']


def episode_search(
	tvshow_tvdb_id: int,
	airdate: str,
	token: str = None
) -> list:
	params = {'firstAired': airdate}
	try:
		resp = _send_request(
			'/series/{}/episodes/query'.format(tvshow_tvdb_id),
			params,
			token=token
		)
	except TVDBException as e:
		if 'No results for your query' in str(e):
			resp = {'data': []}
		else:
			raise
	return resp['data']


def get_poster(tvdb_id: int) -> Response:
	filename = get_static_file('/images/poster_{}.jpg'.format(tvdb_id))
	if not os.path.exists(filename):
		try:
			params = {'keyType': 'poster'}
			resp = _send_request('/series/{}/images/query'.format(tvdb_id), params)['data']
		except TVDBException as e:
			print(e)
			return None
		if len(resp) > 0:
			top_poster = resp[0]
			for r in resp:
				if r['ratingsInfo']['average'] > top_poster['ratingsInfo']['average']:
					top_poster = r
		url = 'http://thetvdb.com/banners/{}'.format(top_poster['fileName'])
		fetch_image(filename, url)
	return serve_static_file('images/poster_{}.jpg'.format(tvdb_id))


def _episode_image_filename(tvdb_id: int) -> Response:
	return get_static_file(f'/images/episode_{tvdb_id}.jpg')


def episode_image(tvdb_id: int) -> Response:
	return serve_static_file(f'images/episode_{tvdb_id}.jpg')


@celery.task(queue='scheduler')
def fetch_episode_image(tvdb_id: int):
	filename = _episode_image_filename(tvdb_id)
	if not os.path.exists(filename):
		print(f'Fetching episode {tvdb_id} image')
		try:
			resp = _send_request(f'/episodes/{tvdb_id}')['data']
		except TVDBException as e:
			print(e)
			return None
		if resp['filename']:
			url = 'http://thetvdb.com/banners/{}'.format(resp['filename'])
			fetch_image(filename, url)
