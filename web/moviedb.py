
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


def image_search(movie_moviedb_id):
	params = {}
	resp = moviedb_request('https://api.themoviedb.org/3/movie/%s' % movie_moviedb_id, params)
	return resp


def get_poster(moviedb_id):
	if not os.path.exists(get_file_location('/static/images/movie_poster_%s.jpg' % moviedb_id)):
		resp = image_search(moviedb_id)
		poster_path = resp['poster_path']
		if poster_path:
			try:
				urlretrieve('https://image.tmdb.org/t/p/w640%s' % poster_path, get_file_location('/static/images/movie_poster_%s.jpg' % moviedb_id))
				img = Image.open(get_file_location('/static/images/movie_poster_%s.jpg' % moviedb_id))
				img_scaled = img.resize((int(img.size[0]/2),int(img.size[1]/2)), Image.ANTIALIAS)
				img_scaled.save(get_file_location('/static/images/movie_poster_%s.jpg' % moviedb_id), optimize=True, quality=95)
			except HTTPError:
				return None
		else:
			return None
	return url_for('static', filename='images/movie_poster_%s.jpg' % moviedb_id)
