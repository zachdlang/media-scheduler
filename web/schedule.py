
from web.utility import *
from web import tvdb, moviedb

schedule = Blueprint('schedule', __name__)


@schedule.route('/login', methods=['GET','POST'])
def login():
	if is_logged_in():
		return redirect(url_for('schedule.home'))

	if request.method == 'POST':
		params = params_to_dict(request.form)
		cursor = g.conn.cursor()
		cursor.execute("""SELECT * FROM app.enduser WHERE TRIM(username) = TRIM(%s)""", (params['username'],))
		resp = query_to_dict_list(cursor)[0]
		ok, new_hash = g.passwd_context.verify_and_update(params['password'].strip(), resp['password'].strip())
		if ok:
			if new_hash:
				cursor.execute("""UPDATE app.enduser SET password = %s WHERE id = %s""", (new_hash, resp['id'],))
				g.conn.commit()
			session.new = True
			session.permanent = True
			session['userid'] = resp['id']
		cursor.close()
			
		if ok:
			return redirect(url_for('schedule.home'))
		else:
			flash('Login failed.', 'danger')
			return redirect(url_for('schedule.login'))

	return render_template('login.html')


@schedule.route('/logout', methods=['GET'])
def logout():
	session.pop('userid', None)
	return redirect(url_for('schedule.login'))


@schedule.route('/', methods=['GET'])
@login_required
def home():
	cursor = g.conn.cursor()
	qry = """SELECT e.*,
				s.name AS show_name,
				s.tvdb_id AS show_tvdb_id, 
				to_char(e.airdate, 'Day DD/MM/YYYY') AS airdate_str, 
				e.airdate < current_date AS in_past 
			FROM episode e
			LEFT JOIN tvshow s ON (s.id = e.tvshowid)
			WHERE follows_episode(%s, e.id) 
			ORDER BY e.airdate, show_name, e.seasonnumber, e.episodenumber"""
	cursor.execute(qry, (session['userid'],))
	episodes = query_to_dict_list(cursor)
	cursor.close()
	outstanding = any(e['in_past'] is True for e in episodes)
	dates = []
	for e in episodes:
		if e['in_past'] is False and e['airdate_str'] not in dates:
			dates.append(e['airdate_str'])
		e['poster'] = tvdb.get_poster(e['show_tvdb_id'])
	return render_template('schedule.html', outstanding=outstanding, dates=dates, episodes=episodes)


@schedule.route('/shows/watched', methods=['POST'])
@login_required
def shows_watched():
	error = None
	params = params_to_dict(request.form)
	episodeid = params.get('episodeid')
	if episodeid:
		cursor = g.conn.cursor()
		try:
			cursor.execute("""SELECT mark_episode_watched(%s, %s)""", (session['userid'], episodeid,))
			g.conn.commit()
		except psycopg2.DatabaseError:
			g.conn.rollback()
			cursor.close()
			raise
		cursor.close()
	else:
		error = 'Please select an episode.'
	return jsonify(error=error)


@schedule.route('/shows', methods=['GET'])
@login_required
def shows():
	return render_template('shows.html')


@schedule.route('/shows/list', methods=['GET'])
@login_required
def shows_list():
	cursor = g.conn.cursor()
	cursor.execute("""SELECT id, tvdb_id, name FROM tvshow WHERE follows_tvshow(%s, id) ORDER BY name ASC""", (session['userid'],))
	shows = query_to_dict_list(cursor)
	cursor.close()
	for s in shows:
		s['poster'] = tvdb.get_poster(s['tvdb_id'])
		s['update_url'] = url_for('schedule.shows_update', tvshowid=s['id'])
		del s['tvdb_id']
	return jsonify(shows=shows)


@schedule.route('/shows/search', methods=['GET'])
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
			result.append({ 'id':r['id'], 'name':r['seriesName'], 'banner':r['banner'], 'year':year })
	return jsonify(error=error, result=result)


@schedule.route('/shows/follow', methods=['POST'])
@login_required
def shows_follow():
	error = None
	params = params_to_dict(request.form)
	tvdb_id = params.get('tvdb_id')
	name = params.get('name')
	if tvdb_id and name:
		cursor = g.conn.cursor()
		cursor.execute("""SELECT * FROM tvshow WHERE tvdb_id = %s""", (tvdb_id,))
		if cursor.rowcount <= 0:
			cursor.execute("""INSERT INTO tvshow (name, tvdb_id) VALUES (%s, %s) RETURNING id""", (name, tvdb_id,))
		tvshowid = query_to_dict_list(cursor)[0]['id']
		tvdb.get_poster(tvdb_id)
		# Only add link if one doesn't already exist
		cursor.execute("""SELECT add_watcher_tvshow(%s, %s)""", (session['userid'], tvshowid,))
		g.conn.commit()
		cursor.close()
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@schedule.route('/shows/unfollow', methods=['POST'])
@login_required
def shows_unfollow():
	error = None
	params = params_to_dict(request.form)
	tvshowid = params.get('tvshowid')
	if tvshowid:
		cursor = g.conn.cursor()
		cursor.execute("""SELECT remove_watcher_tvshow(%s, %s)""", (session['userid'], tvshowid,))
		g.conn.commit()
		cursor.close()
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@schedule.route('/movies', methods=['GET'])
@login_required
def movies():
	return render_template('movies.html')


@schedule.route('/movies/list', methods=['GET'])
@login_required
def movies_list():
	cursor = g.conn.cursor()
	qry = """SELECT m.*,
				COALESCE(to_char(m.releasedate, 'DD/MM/YYYY'), 'TBD') AS releasedate_str, 
				m.releasedate < current_date AS in_past 
			FROM movie m
			WHERE follows_movie(%s, m.id) 
			ORDER BY m.releasedate NULLS LAST, m.name"""
	cursor.execute(qry, (session['userid'],))
	movies = query_to_dict_list(cursor)
	cursor.close()
	outstanding = []
	dates = []
	for m in movies:
		if m['in_past'] is False and m['releasedate_str'] not in [ x['date'] for x in dates ]:
			dates.append({ 'date':m['releasedate_str'] })
		elif m['in_past'] is True:
			outstanding.append(m)
		m['poster'] = moviedb.get_poster(m['moviedb_id'])
		m['update_url'] = url_for('schedule.movies_update', movieid=m['id'])
	dates.append({ 'date':'TBD' })

	for d in dates:
		d['movies'] = []
		for m in movies:
			if m['releasedate_str'] == d['date']:
				d['movies'].append(m)

	return jsonify(dates=dates, outstanding=outstanding)


@schedule.route('/movies/watched', methods=['POST'])
@login_required
def movies_watched():
	error = None
	params = params_to_dict(request.form)
	movieid = params.get('movieid')
	if movieid:
		cursor = g.conn.cursor()
		try:
			cursor.execute("""SELECT mark_movie_watched(%s, %s)""", (session['userid'], movieid,))
			g.conn.commit()
		except psycopg2.DatabaseError:
			g.conn.rollback()
			cursor.close()
			raise
		cursor.close()
	else:
		error = 'Please select an movie.'
	return jsonify(error=error)


@schedule.route('/movies/search', methods=['GET'])
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
			result.append({ 'id':r['id'], 'name':r['title'], 'releasedate':r['release_date'], 'poster':r['poster_path'], 'year':year })
	return jsonify(error=error, result=result)


@schedule.route('/movies/follow', methods=['POST'])
@login_required
def movies_follow():
	error = None
	params = params_to_dict(request.form)
	moviedb_id = params.get('moviedb_id')
	name = params.get('name')
	releasedate = params.get('releasedate')
	if moviedb_id and name:
		cursor = g.conn.cursor()
		cursor.execute("""SELECT * FROM movie WHERE moviedb_id = %s""", (moviedb_id,))
		if cursor.rowcount <= 0:
			cursor.execute("""INSERT INTO movie (name, releasedate, moviedb_id) VALUES (%s, %s, %s) RETURNING id""", (name, releasedate, moviedb_id,))
		movieid = query_to_dict_list(cursor)[0]['id']
		moviedb.get_poster(moviedb_id)
		# Only add link if one doesn't already exist
		cursor.execute("""SELECT add_watcher_movie(%s, %s)""", (session['userid'], movieid,))
		g.conn.commit()
		cursor.close()
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@schedule.route('/shows/update', methods=['GET'])
@schedule.route('/shows/update/<int:tvshowid>', methods=['GET'])
def shows_update(tvshowid=None):
	error = None
	cursor = g.conn.cursor()

	if tvshowid is not None:
		qry = """SELECT * FROM tvshow WHERE id = %s"""
		qargs = (tvshowid,)
	else:
		# Only check shows with followers to save time & requests
		qry = """SELECT * FROM tvshow WHERE exists(SELECT * FROM watcher_tvshow WHERE tvshowid = tvshow.id) ORDER BY name ASC"""
		qargs = None

	cursor.execute(qry, qargs)
	tvshows = query_to_dict_list(cursor)
	
	updated = 0
	for n in range(0, 31):
		# minus 1 day to account for US airdates compared to NZ airdates
		airdate = (datetime.datetime.today() + datetime.timedelta(days=n - 1)).strftime('%Y-%m-%d')
		print('Checking date %s' % airdate)
		for s in tvshows:
			resp = tvdb.episode_search(s['tvdb_id'], airdate)
			if resp:
				print('Found for %s' % s['name'])
				for r in resp:
					if r['episodeName'] is None:
						r['episodeName'] = 'Season %s Episode %s' % (r['airedSeason'], r['airedEpisodeNumber'])
					r['episodeName'] = strip_unicode_characters(r['episodeName'])
					cursor.execute("""SELECT *, (airdate - '1 day'::INTERVAL)::DATE::TEXT AS airdate FROM episode WHERE tvdb_id = %s""", (r['id'],))
					if cursor.rowcount <= 0:
						# add 1 day to account for US airdates compared to NZ airdates
						qry = """INSERT INTO episode (tvshowid, seasonnumber, episodenumber, name, airdate, tvdb_id) VALUES (%s, %s, %s, %s, (%s::DATE + '1 day'::INTERVAL), %s) RETURNING id"""
						qargs = (s['id'], r['airedSeason'], r['airedEpisodeNumber'], strip_unicode_characters(r['episodeName']), r['firstAired'], r['id'],)
						try:
							cursor.execute(qry, qargs)
							g.conn.commit()
						except psycopg2.DatabaseError:
							g.conn.rollback()
							cursor.close()
							raise
						updated += 1
					else:
						print('%s episode %s is not new' % (s['name'], r['id']))
						episode = cursor.fetchone()
						# I didn't like the long if statement
						checkfor = [
							{ 'local':episode['name'], 'remote':r['episodeName'] },
							{ 'local':episode['airdate'], 'remote':r['firstAired'] },
							{ 'local':episode['seasonnumber'], 'remote':r['airedSeason'] },
							{ 'local':episode['episodenumber'], 'remote':r['airedEpisodeNumber'] }
						]
						changed = False
						for c in checkfor:
							if str(c['local']) != str(c['remote']):
								changed = True
						if changed:
							print('%s episode %s has changed' % (s['name'], episode['name']))
							try:
								qry = """UPDATE episode SET name = %s, airdate = (%s::DATE + '1 day'::INTERVAL), seasonnumber = %s, episodenumber = %s WHERE id = %s"""
								qargs = (strip_unicode_characters(r['episodeName']), r['firstAired'], r['airedSeason'], r['airedEpisodeNumber'], episode['id'],)
								cursor.execute(qry, qargs)
								g.conn.commit()
							except psycopg2.DatabaseError:
								g.conn.rollback()
								cursor.close()
								raise
							updated += 1
	cursor.close()

	# with tvshowid parameter, is being called from page instead of cron
	if tvshowid is not None:
		flash('Updated %s episodes.' % updated, 'success')
		return redirect(url_for('schedule.home'))

	return jsonify(error=error)


@schedule.route('/movies/update', methods=['GET'])
@schedule.route('/movies/update/<int:movieid>', methods=['GET'])
def movies_update(movieid=None):
	error = None
	cursor = g.conn.cursor()

	if movieid is not None:
		qry = """SELECT * FROM movie WHERE id = %s"""
		qargs = (movieid,)
	else:
		# Only check movies with followers to save time & requests
		qry = """SELECT * FROM movie WHERE exists(SELECT * FROM watcher_movie WHERE movieid = movie.id AND watched = false) ORDER BY name ASC"""
		qargs = None

	cursor.execute(qry, qargs)
	movies = query_to_dict_list(cursor)
	
	for m in movies:
		resp = moviedb.get(m['moviedb_id'])
		changed = False
		if m['name'] != resp['title']:
			changed = True
		if m['releasedate'] is not None:
			m['releasedate'] = m['releasedate'].strftime("%Y-%m-%d")
			if m['releasedate'] != resp['release_date']:
				changed = True

		if changed:
			print('"%s" (%s) changed to "%s" (%s)' % (m['name'], m['releasedate'], resp['title'], resp['release_date']))
			try:
				cursor.execute("""UPDATE movie SET name = %s, releasedate = %s WHERE id = %s""", (resp['title'], resp['release_date'], m['id'],))
				g.conn.commit()
			except psycopg2.DatabaseError:
				g.conn.rollback()
				cursor.close()
				raise

	cursor.close()

	if movieid is not None:
		return redirect(url_for('schedule.movies'))

	return jsonify(error=error)