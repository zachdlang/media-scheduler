# Standard library imports
import datetime
import logging
from logging.handlers import SMTPHandler

# Third party imports
from flask import (
	send_from_directory, request, session, url_for, redirect,
	flash, render_template, jsonify
)

# Local imports
from web import tvdb, moviedb
from sitetools.utility import (
	BetterExceptionFlask, is_logged_in, params_to_dict,
	login_required, strip_unicode_characters, check_login,
	fetch_query, mutate_query, disconnect_database,
	handle_exception, setup_celery, check_celery_running
)

app = BetterExceptionFlask(__name__)

app.config.from_pyfile('site_config.cfg')
app.secret_key = app.config['SECRETKEY']

celery = setup_celery(app)

app.jinja_env.globals.update(is_logged_in=is_logged_in)

if not app.debug:
	ADMINISTRATORS = [app.config['TO_EMAIL']]
	msg = 'Internal Error on scheduler'
	mail_handler = SMTPHandler('127.0.0.1', app.config['FROM_EMAIL'], ADMINISTRATORS, msg)
	mail_handler.setLevel(logging.CRITICAL)
	app.logger.addHandler(mail_handler)


@app.errorhandler(500)
def internal_error(e):
	return handle_exception


@app.teardown_appcontext
def teardown(error):
	disconnect_database()


@app.route('/favicon.ico')
@app.route('/robots.txt')
@app.route('/sitemap.xml')
def static_from_root():
	return send_from_directory(app.static_folder, request.path[1:])


@app.route('/login', methods=['GET', 'POST'])
def login():
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
def logout():
	session.pop('userid', None)
	return redirect(url_for('login'))


@app.route('/', methods=['GET'])
@login_required
def home():
	qry = """SELECT e.*,
				s.name AS show_name,
				s.tvdb_id AS show_tvdb_id,
				to_char(e.airdate, 'Day DD/MM/YYYY') AS airdate_str,
				e.airdate < current_date AS in_past
			FROM episode e
			LEFT JOIN tvshow s ON (s.id = e.tvshowid)
			WHERE follows_episode(%s, e.id)
			ORDER BY e.airdate, show_name, e.seasonnumber, e.episodenumber"""
	episodes = fetch_query(qry, (session['userid'],))
	outstanding = any(e['in_past'] is True for e in episodes)
	dates = []
	for e in episodes:
		if e['in_past'] is False and e['airdate_str'] not in dates:
			dates.append(e['airdate_str'])
		e['poster'] = tvdb.get_poster(e['show_tvdb_id'])
	return render_template('schedule.html', outstanding=outstanding, dates=dates, episodes=episodes)


@app.route('/shows/watched', methods=['POST'])
@login_required
def shows_watched():
	error = None
	params = params_to_dict(request.form)
	episodeid = params.get('episodeid')
	if episodeid:
		mutate_query("SELECT mark_episode_watched(%s, %s)", (session['userid'], episodeid,))
	else:
		error = 'Please select an episode.'
	return jsonify(error=error)


@app.route('/shows', methods=['GET'])
@login_required
def shows():
	return render_template('shows.html')


@app.route('/shows/list', methods=['GET'])
@login_required
def shows_list():
	qry = "SELECT id, tvdb_id, name FROM tvshow WHERE follows_tvshow(%s, id) ORDER BY name ASC"
	shows = fetch_query(qry, (session['userid'],))
	for s in shows:
		s['poster'] = tvdb.get_poster(s['tvdb_id'])
		s['update_url'] = url_for('shows_update', tvshowid=s['id'])
		del s['tvdb_id']
	return jsonify(shows=shows)


@app.route('/shows/search', methods=['GET'])
@login_required
def shows_search():
	error = None
	result = []
	params = params_to_dict(request.args)
	search = params.get('search')
	if search:
		resp = tvdb.series_search(search)
		for r in resp:
			year = datetime.datetime.strptime(r['firstAired'], '%Y-%m-%d').year if r['firstAired'] else None
			result.append({
				'id': r['id'],
				'name': r['seriesName'],
				'banner': r['banner'],
				'year': year
			})
	return jsonify(error=error, result=result)


@app.route('/shows/follow', methods=['POST'])
@login_required
def shows_follow():
	error = None
	params = params_to_dict(request.form)
	tvdb_id = params.get('tvdb_id')
	name = params.get('name')
	if tvdb_id and name:
		tvshow = fetch_query("SELECT id FROM tvshow WHERE tvdb_id = %s", (tvdb_id,), single_row=True)
		if not tvshow:
			qry = "INSERT INTO tvshow (name, tvdb_id) VALUES (%s, %s) RETURNING id"
			tvshow = mutate_query(qry, (name, tvdb_id,), returning=True)
		mutate_query("SELECT add_watcher_tvshow(%s, %s)", (session['userid'], tvshow['id'],))
		tvdb.get_poster(tvdb_id)
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@app.route('/shows/unfollow', methods=['POST'])
@login_required
def shows_unfollow():
	error = None
	params = params_to_dict(request.form)
	tvshowid = params.get('tvshowid')
	if tvshowid:
		mutate_query("SELECT remove_watcher_tvshow(%s, %s)", (session['userid'], tvshowid,))
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@app.route('/movies', methods=['GET'])
@login_required
def movies():
	return render_template('movies.html')


@app.route('/movies/list', methods=['GET'])
@login_required
def movies_list():
	qry = """SELECT m.*,
				COALESCE(to_char(m.releasedate, 'DD/MM/YYYY'), 'TBD') AS releasedate_str,
				m.releasedate < current_date AS in_past
			FROM movie m
			WHERE follows_movie(%s, m.id)
			ORDER BY m.releasedate NULLS LAST, m.name"""
	movies = fetch_query(qry, (session['userid'],))
	outstanding = []
	dates = []
	for m in movies:
		if m['in_past'] is False and m['releasedate_str'] not in [x['date'] for x in dates]:
			dates.append({'date': m['releasedate_str']})
		elif m['in_past'] is True:
			outstanding.append(m)
		m['poster'] = moviedb.get_poster(m['moviedb_id'])
		m['update_url'] = url_for('movies_update', movieid=m['id'])
	dates.append({'date': 'TBD'})

	for d in dates:
		d['movies'] = []
		for m in movies:
			if m['releasedate_str'] == d['date']:
				d['movies'].append(m)

	return jsonify(dates=dates, outstanding=outstanding)


@app.route('/movies/watched', methods=['POST'])
@login_required
def movies_watched():
	error = None
	params = params_to_dict(request.form)
	movieid = params.get('movieid')
	if movieid:
		mutate_query("SELECT mark_movie_watched(%s, %s)", (session['userid'], movieid,))
	else:
		error = 'Please select an movie.'
	return jsonify(error=error)


@app.route('/movies/search', methods=['GET'])
@login_required
def movies_search():
	error = None
	result = []
	params = params_to_dict(request.args)
	search = params.get('search')
	if search:
		resp = moviedb.search(search)
		for r in resp:
			year = datetime.datetime.strptime(r['release_date'], '%Y-%m-%d').year if r['release_date'] else None
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
def movies_follow():
	error = None
	params = params_to_dict(request.form)
	moviedb_id = params.get('moviedb_id')
	name = params.get('name')
	releasedate = params.get('releasedate')
	if moviedb_id and name:
		movie = fetch_query("SELECT * FROM movie WHERE moviedb_id = %s", (moviedb_id,), single_row=True)
		if not movie:
			qry = "INSERT INTO movie (name, releasedate, moviedb_id) VALUES (%s, %s, %s) RETURNING id"
			movie = mutate_query(qry, (name, releasedate, moviedb_id,), returning=True)
		mutate_query("SELECT add_watcher_movie(%s, %s)", (session['userid'], movie['id'],))
		moviedb.get_poster(moviedb_id)
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@app.route('/shows/update', methods=['GET'])
@app.route('/shows/update/<int:tvshowid>', methods=['GET'])
@check_celery_running
def shows_update(tvshowid=None):
	error = None

	if tvshowid is not None:
		qry = "SELECT * FROM tvshow WHERE id = %s"
		qargs = (tvshowid,)
	else:
		# Only check shows with followers to save time & requests
		qry = "SELECT * FROM tvshow WHERE exists(SELECT * FROM watcher_tvshow WHERE tvshowid = tvshow.id) ORDER BY name ASC"
		qargs = None

	tvshows = fetch_query(qry, qargs)

	tvdb_token = tvdb.login()

	for n in range(0, 31):
		# minus 1 day to account for US airdates compared to NZ airdates
		airdate = (datetime.datetime.today() + datetime.timedelta(days=n - 1)).strftime('%Y-%m-%d')
		for s in tvshows:
			resync_tvshow.delay(airdate, s, tvdb_token)

	# with tvshowid parameter, is being called from page instead of cron
	if tvshowid is not None:
		flash('Updating episodes.', 'success')
		return redirect(url_for('home'))

	return jsonify(error=error)


@celery.task()
def resync_tvshow(airdate, tvshow, tvdb_token):
	print('Checking date %s for %s' % (airdate, tvshow['name']))
	resp = tvdb.episode_search(tvshow['tvdb_id'], airdate, token=tvdb_token)
	if resp:
		print('Found for %s' % tvshow['name'])
		for r in resp:
			if r['episodeName'] is None:
				r['episodeName'] = 'Season %s Episode %s' % (r['airedSeason'], r['airedEpisodeNumber'])
			r['episodeName'] = strip_unicode_characters(r['episodeName'])

			qry = "SELECT *, (airdate - '1 day'::INTERVAL)::DATE::TEXT AS airdate FROM episode WHERE tvdb_id = %s"
			existing = fetch_query(qry, (r['id'],), single_row=True)
			if not existing:
				# add 1 day to account for US airdates compared to NZ airdates
				qry = """INSERT INTO episode (tvshowid, seasonnumber, episodenumber, name, airdate, tvdb_id)
						VALUES (%s, %s, %s, %s, (%s::DATE + '1 day'::INTERVAL), %s) RETURNING id"""
				qargs = (
					tvshow['id'], r['airedSeason'], r['airedEpisodeNumber'],
					strip_unicode_characters(r['episodeName']),
					r['firstAired'], r['id'],
				)
				mutate_query(qry, qargs)
			else:
				print('%s episode %s is not new' % (tvshow['name'], r['id']))
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
					print('%s episode %s has changed' % (tvshow['name'], existing['name']))
					qry = """UPDATE episode SET name = %s, airdate = (%s::DATE + '1 day'::INTERVAL),
								seasonnumber = %s, episodenumber = %s
							WHERE id = %s"""
					qargs = (
						strip_unicode_characters(r['episodeName']), r['firstAired'],
						r['airedSeason'], r['airedEpisodeNumber'], existing['id'],
					)
					mutate_query(qry, qargs)


@app.route('/movies/update', methods=['GET'])
@app.route('/movies/update/<int:movieid>', methods=['GET'])
@check_celery_running
def movies_update(movieid=None):
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


@celery.task()
def resync_movie(movie):
	print('Resyncing %s' % movie['name'])
	resp = moviedb.get(movie['moviedb_id'])
	changed = False
	if movie['name'] != resp['title']:
		changed = True
	if movie['releasedate'] is not None:
		movie['releasedate'] = datetime.datetime.strptime(movie['releasedate'], '%Y-%m-%d').strftime("%Y-%m-%d")
		if movie['releasedate'] != resp['release_date']:
			changed = True

	if changed:
		print('"%s" (%s) changed to "%s" (%s)' % (movie['name'], movie['releasedate'], resp['title'], resp['release_date']))
		qry = "UPDATE movie SET name = %s, releasedate = %s WHERE id = %s"
		qargs = (resp['title'], resp['release_date'], movie['id'],)
		mutate_query(qry, qargs)


if __name__ == '__main__':
	app.run()
