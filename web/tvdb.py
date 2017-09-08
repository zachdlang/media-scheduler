
from web.utility import *


def get_headers():
	headers = { 
		'Content-Type':'application/json', 
		'Accept':'application/json', 
		'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
	}
	return headers


def login():
	data = { 'apikey':g.config['TVDB_APIKEY'], 'userkey':g.config['TVDB_USERKEY'], 'username':g.config['TVDB_USERNAME'] }
	headers = get_headers()
	r = requests.post('https://api.thetvdb.com/login', data=json.dumps(data), headers=headers).text
	resp = json.loads(r)
	if 'Error' in resp:
		raise Exception(resp['Error'])
	session['tvdb_token'] = resp['token']


def tvdb_request(url, params):
	if 'tvdb_token' not in session:
		login()
	headers = get_headers()
	headers['Authorization'] = 'Bearer %s' % session['tvdb_token']
	r = requests.get(url, params=params, headers=headers).text
	resp = json.loads(r)
	if 'Error' in resp:
		if resp['Error'].lower() == 'not authorized':
			login()
			# Refresh token and try again
			headers['Authorization'] = 'Bearer %s' % session['tvdb_token']
			r = requests.get(url, params=params, headers=headers).text
			resp = json.loads(r)
			if 'Error' in resp:
				raise Exception(resp['Error'])
		else:
			raise Exception(resp['Error'])
	return resp


def series_search(name):
	params = { 'name':name }
	resp = tvdb_request('https://api.thetvdb.com/search/series', params)
	return resp['data']


def episode_search(tvshow_tvdb_id, airdate):
	params = { 'firstAired':airdate }
	try:
		resp = tvdb_request('https://api.thetvdb.com/series/%s/episodes/query' % tvshow_tvdb_id, params)
	except Exception as e:
		if 'No results for your query' in str(e):
			resp = { 'data':[] }
		else:
			raise
	return resp['data']


def image_search(tvshow_tvdb_id):
	params = { 'keyType':'poster' }
	resp = tvdb_request('https://api.thetvdb.com/series/%s/images/query' % tvshow_tvdb_id, params)
	return resp['data']
