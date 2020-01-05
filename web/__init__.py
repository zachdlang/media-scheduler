# Standard library imports
from datetime import datetime, timedelta

# Third party imports
from flask import (
	send_from_directory, request, session, url_for, redirect,
	flash, render_template, jsonify, Flask, Response
)
from flask_cors import CORS
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# Local imports
from web import moviedb, config
from flasktools import (
	handle_exception, params_to_dict, strip_unicode_characters,
	serve_static_file
)
from flasktools.auth import is_logged_in, check_login, login_required
from flasktools.celery import setup_celery
from flasktools.db import disconnect_database, fetch_query, mutate_query


if not hasattr(config, 'TESTMODE'):
	sentry_sdk.init(
		dsn=config.SENTRY_DSN,
		integrations=[
			FlaskIntegration(),
			CeleryIntegration(),
			RedisIntegration()
		]
	)

app = Flask(__name__)

app.secret_key = config.SECRETKEY

# enable CORS
CORS(app, resources={r'/*': {'origins': '*'}})

celery = setup_celery(app)

from web import tvdb
from web.episode import bp as episode_bp

app.register_blueprint(episode_bp, url_prefix='/episode')

app.jinja_env.globals.update(is_logged_in=is_logged_in)
app.jinja_env.globals.update(static_file=serve_static_file)


@app.errorhandler(500)
def internal_error(e: Exception) -> Response:
	return handle_exception()


@app.teardown_appcontext
def teardown(e: Exception) -> Response:
	disconnect_database()


@app.route('/ping')
def ping() -> Response:
	return jsonify(ping='pong')


@app.route('/favicon.ico')
@app.route('/robots.txt')
@app.route('/sitemap.xml')
def static_from_root() -> Response:
	return send_from_directory(app.static_folder, request.path[1:])


@app.route('/login', methods=['GET', 'POST'])
def login() -> Response:
	if is_logged_in():
		return redirect(url_for('home'))

	if request.method == 'POST':
		params = params_to_dict(request.form)

		ok = check_login(params.get('username'), params.get('password'))

		if ok:
			return redirect(url_for('home'))
		else:
			flash('Login failed.', 'danger')
			return redirect(url_for('login'))

	return render_template('login.html')


@app.route('/logout', methods=['GET'])
def logout() -> Response:
	session.pop('userid', None)
	return redirect(url_for('login'))


@app.route('/', methods=['GET'])
@login_required
def home() -> Response:
	episodes = fetch_query(
		"""
		SELECT
			e.id, e.seasonnumber,
			e.episodenumber, e.name,
			s.name AS show_name,
			s.tvdb_id AS show_tvdb_id,
			to_char(e.airdate, 'Day DD/MM/YYYY') AS airdate_str,
			e.airdate < current_date AS in_past
		FROM episode e
		LEFT JOIN tvshow s ON (s.id = e.tvshowid)
		WHERE follows_episode(%s, e.id)
		ORDER BY e.airdate, show_name, e.seasonnumber, e.episodenumber
		""",
		(session['userid'],)
	)
	outstanding = any(e['in_past'] is True for e in episodes)
	dates = []
	for e in episodes:
		if e['in_past'] is False and e['airdate_str'] not in dates:
			dates.append(e['airdate_str'])
		e['poster'] = tvdb.get_poster(e['show_tvdb_id'])
		if not e['poster']:
			e['poster'] = serve_static_file('img/placeholder.jpg')
	return render_template(
		'schedule.html',
		outstanding=outstanding,
		dates=dates,
		episodes=episodes
	)


@app.route('/shows/watched', methods=['POST'])
@login_required
def shows_watched() -> Response:
	error = None
	params = params_to_dict(request.form)
	episodeid = params.get('episodeid')
	if episodeid:
		mutate_query(
			"SELECT mark_episode_watched(%s, %s)",
			(session['userid'], episodeid,)
		)
	else:
		error = 'Please select an episode.'
	return jsonify(error=error)


@app.route('/shows', methods=['GET'])
@login_required
def shows() -> Response:
	return render_template('shows.html')


@app.route('/shows/list', methods=['GET'])
@login_required
def shows_list() -> Response:
	shows = fetch_query(
		"""
		SELECT
			id, tvdb_id, name
		FROM tvshow
		WHERE follows_tvshow(%s, id)
		ORDER BY name ASC
		""",
		(session['userid'],)
	)
	for s in shows:
		s['poster'] = tvdb.get_poster(s['tvdb_id'])
		if not s['poster']:
			s['poster'] = serve_static_file('img/placeholder.jpg')
		s['update_url'] = url_for('shows_update', tvshowid=s['id'])
		del s['tvdb_id']
	return jsonify(shows=shows)


@app.route('/shows/search', methods=['GET'])
@login_required
def shows_search() -> Response:
	error = None
	result = []
	params = params_to_dict(request.args)
	search = params.get('search')
	if search:
		resp = tvdb.series_search(search)
		for r in resp:
			year = None
			if r['firstAired']:
				year = datetime.strptime(r['firstAired'], '%Y-%m-%d').year
			result.append({
				'id': r['id'],
				'name': r['seriesName'],
				'banner': r['banner'],
				'year': year
			})
	return jsonify(error=error, result=result)


@app.route('/shows/follow', methods=['POST'])
@login_required
def shows_follow() -> Response:
	error = None
	params = params_to_dict(request.form)
	tvdb_id = params.get('tvdb_id')
	name = params.get('name')
	if tvdb_id and name:
		tvshow = fetch_query(
			"SELECT id FROM tvshow WHERE tvdb_id = %s",
			(tvdb_id,),
			single_row=True
		)
		if not tvshow:
			tvshow = mutate_query(
				"INSERT INTO tvshow (name, tvdb_id) VALUES (%s, %s) RETURNING id",
				(name, tvdb_id,),
				returning=True
			)
		mutate_query(
			"SELECT add_watcher_tvshow(%s, %s)",
			(session['userid'], tvshow['id'],)
		)
		tvdb.get_poster(tvdb_id)
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@app.route('/shows/unfollow', methods=['POST'])
@login_required
def shows_unfollow() -> Response:
	error = None
	params = params_to_dict(request.form)
	tvshowid = params.get('tvshowid')
	if tvshowid:
		mutate_query(
			"SELECT remove_watcher_tvshow(%s, %s)",
			(session['userid'], tvshowid,)
		)
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@app.route('/movies', methods=['GET'])
@login_required
def movies() -> Response:
	return render_template('movies.html')


@app.route('/movies/list', methods=['GET'])
@login_required
def movies_list() -> Response:
	movies = fetch_query(
		"""
		SELECT
			m.id, m.name, m.moviedb_id,
			COALESCE(to_char(m.releasedate, 'DD/MM/YYYY'), 'TBD') AS releasedate_str,
			m.releasedate < current_date AS in_past
		FROM movie m
		WHERE follows_movie(%s, m.id)
		ORDER BY m.releasedate NULLS LAST, m.name
		""",
		(session['userid'],)
	)
	outstanding = []
	dates = []
	count = 0
	for m in movies:
		existing_date = m['releasedate_str'] in [x['date'] for x in dates]
		if m['in_past'] is False and not existing_date:
			dates.append({'date': m['releasedate_str']})
		elif m['in_past'] is True:
			outstanding.append(m)
		m['poster'] = moviedb.get_poster(m['moviedb_id'])
		if not m['poster']:
			m['poster'] = serve_static_file('img/placeholder.jpg')
		m['update_url'] = url_for('movies_update', movieid=m['id'])
		count += 1
	dates.append({'date': 'TBD'})

	for d in dates:
		d['movies'] = []
		for m in movies:
			if m['releasedate_str'] == d['date']:
				d['movies'].append(m)

	return jsonify(dates=dates, outstanding=outstanding, count=count)


@app.route('/movies/watched', methods=['POST'])
@login_required
def movies_watched() -> Response:
	error = None
	params = params_to_dict(request.form)
	movieid = params.get('movieid')
	if movieid:
		mutate_query(
			"SELECT mark_movie_watched(%s, %s)",
			(session['userid'], movieid,)
		)
	else:
		error = 'Please select an movie.'
	return jsonify(error=error)


@app.route('/movies/search', methods=['GET'])
@login_required
def movies_search() -> Response:
	error = None
	result = []
	params = params_to_dict(request.args)
	search = params.get('search')
	if search:
		resp = moviedb.search(search)
		for r in resp:
			year = None
			if r['release_date']:
				year = datetime.strptime(r['release_date'], '%Y-%m-%d').year

			result.append({
				'id': r['id'],
				'name': r['title'],
				'releasedate': r['release_date'],
				'poster': r['poster_path'],
				'year': year
			})
	return jsonify(error=error, result=result)


@app.route('/movies/follow', methods=['POST'])
@login_required
def movies_follow() -> Response:
	error = None
	params = params_to_dict(request.form)
	moviedb_id = params.get('moviedb_id')
	name = params.get('name')
	releasedate = params.get('releasedate')
	if moviedb_id and name:
		movie = fetch_query(
			"SELECT * FROM movie WHERE moviedb_id = %s",
			(moviedb_id,),
			single_row=True
		)
		if not movie:
			movie = mutate_query(
				"""
				INSERT INTO movie (
					name, releasedate, moviedb_id
				) VALUES (
					%s, %s, %s
				) RETURNING id
				""",
				(name, releasedate, moviedb_id,),
				returning=True
			)
		mutate_query(
			"SELECT add_watcher_movie(%s, %s)",
			(session['userid'], movie['id'],)
		)
		moviedb.get_poster(moviedb_id)
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@app.route('/shows/update', methods=['GET'])
@app.route('/shows/update/<int:tvshowid>', methods=['GET'])
def shows_update(tvshowid: int = None) -> Response:
	error = None

	if tvshowid is not None:
		tvshows = fetch_query(
			"SELECT id, name, tvdb_id FROM tvshow WHERE id = %s",
			(tvshowid,)
		)
	else:
		# Only check shows with followers to save time & requests
		tvshows = fetch_query(
			"""
			SELECT
				id, name, tvdb_id
			FROM tvshow
			WHERE exists(
				SELECT * FROM watcher_tvshow WHERE tvshowid = tvshow.id
			) ORDER BY name ASC
			"""
		)

	tvdb_token = tvdb.login()

	for n in range(0, 31):
		# minus 1 day to account for US airdates compared to NZ airdates
		airdate = (datetime.today() + timedelta(days=n - 1)).strftime('%Y-%m-%d')
		for s in tvshows:
			resync_tvshow.delay(airdate, s, tvdb_token)

	# with tvshowid parameter, is being called from page instead of cron
	if tvshowid is not None:
		flash('Updating episodes.', 'success')
		return redirect(url_for('home'))

	return jsonify(error=error)


@celery.task(queue='scheduler')
def resync_tvshow(airdate: str, tvshow: dict, tvdb_token: str) -> None:
	print('Checking date {} for {}'.format(airdate, tvshow['name']))
	resp = tvdb.episode_search(tvshow['tvdb_id'], airdate, token=tvdb_token)
	if resp:
		print('Found for %s' % tvshow['name'])
		for r in resp:
			if r['episodeName'] is None:
				r['episodeName'] = 'Season {} Episode {}'.format(
					r['airedSeason'], r['airedEpisodeNumber']
				)
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
						r['airedSeason'],
						r['airedEpisodeNumber'],
						strip_unicode_characters(r['episodeName']),
						r['firstAired'],
						r['id'],
					)
				)
			else:
				print('{} episode {} is not new'.format(tvshow['name'], r['id']))
				# I didn't like the long if statement
				checkfor = [
					{'local': existing['name'], 'remote':r['episodeName']},
					{'local': existing['airdate'], 'remote':r['firstAired']},
					{'local': existing['seasonnumber'], 'remote':r['airedSeason']},
					{'local': existing['episodenumber'], 'remote':r['airedEpisodeNumber']}
				]
				changed = False
				for c in checkfor:
					if str(c['local']) != str(c['remote']):
						changed = True
				if changed:
					print(
						'{} episode {} has changed'.format(
							tvshow['name'], existing['name']
						)
					)
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
							r['airedSeason'],
							r['airedEpisodeNumber'],
							existing['id'],
						)
					)


@app.route('/movies/update', methods=['GET'])
@app.route('/movies/update/<int:movieid>', methods=['GET'])
def movies_update(movieid: int = None) -> Response:
	error = None

	qry = "SELECT *, releasedate::TEXT AS releasedate FROM movie"
	qargs = ()
	if movieid is not None:
		qry += " WHERE id = %s"
		qargs += (movieid,)
	else:
		# Only check movies with followers to save time & requests
		qry += """ WHERE exists(
					SELECT 1
					FROM watcher_movie
					WHERE movieid = movie.id
					AND watched = false
				)"""
	qry += " ORDER BY name ASC"

	movies = fetch_query(qry, qargs)

	for m in movies:
		resync_movie.delay(m)

	if movieid is not None:
		return redirect(url_for('movies'))

	return jsonify(error=error)


@celery.task(queue='scheduler')
def resync_movie(movie: dict) -> None:
	print('Resyncing {}'.format(movie['name']))
	resp = moviedb.get(movie['moviedb_id'])
	changed = False
	if movie['name'] != resp['title']:
		changed = True
	if movie['releasedate'] is not None:
		if movie['releasedate'] != resp['release_date']:
			changed = True

	if changed:
		print(
			'"{}" ({}) changed to "{}" ({})'.format(
				movie['name'],
				movie['releasedate'],
				resp['title'],
				resp['release_date']
			)
		)
		mutate_query(
			"UPDATE movie SET name = %s, releasedate = %s WHERE id = %s",
			(resp['title'], resp['release_date'], movie['id'],)
		)


if __name__ == '__main__':
	app.run()
