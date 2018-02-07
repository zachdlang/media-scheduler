
from web.utility import *


def moviedb_request(url, params):
	params['api_key'] = g.config['MOVIEDB_APIKEY']
	r = requests.get(url, params=params).text
	resp = json.loads(r)
	return resp


def search(name):
	params = { 'query':name }
	resp = moviedb_request('https://api.themoviedb.org/3/search/movie', params)
	return resp['results']


def get(movie_moviedb_id):
	params = {}
	resp = moviedb_request('https://api.themoviedb.org/3/movie/%s' % movie_moviedb_id, params)
	return resp


def image_search(movie_moviedb_id):
	resp = get(movie_moviedb_id)
	params = {}
	conf = moviedb_request('https://api.themoviedb.org/3/configuration', params)
	size = None
	for s in conf['images']['poster_sizes']:
		if size is None and 'w' in s and int(s.replace('w','')) >= 500:
			size = s
	resp['base_url'] = conf['images']['base_url']
	resp['poster_size'] = size
	return resp


def get_poster(moviedb_id):
	if not os.path.exists(get_file_location('/static/images/movie_poster_%s.jpg' % moviedb_id)):
		resp = image_search(moviedb_id)
		poster_path = resp['poster_path']
		if poster_path:
			url = '%s%s%s' % (resp['base_url'], resp['poster_size'], resp['poster_path'])
			urlretrieve(url, get_file_location('/static/images/movie_poster_%s.jpg' % moviedb_id))
			img = Image.open(get_file_location('/static/images/movie_poster_%s.jpg' % moviedb_id))
			img_scaled = img.resize((int(img.size[0]/2),int(img.size[1]/2)), Image.ANTIALIAS)
			img_scaled.save(get_file_location('/static/images/movie_poster_%s.jpg' % moviedb_id), optimize=True, quality=95)
		else:
			return None
	return url_for('static', filename='images/movie_poster_%s.jpg' % moviedb_id)
