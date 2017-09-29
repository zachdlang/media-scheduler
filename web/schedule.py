
from web.utility import *
from web import tvdb

schedule = Blueprint('schedule', __name__)


@schedule.route('/shows', methods=['GET'])
@login_required
def shows():
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


@schedule.route('/update', methods=['GET'])
def update():
	error = None
	cursor = g.conn.cursor()
	cursor.execute("""SELECT * FROM tvshow ORDER BY name ASC""")
	tvshows = query_to_dict_list(cursor)
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
						qargs = (s['id'], r['airedSeason'], r['airedEpisodeNumber'], r['episodeName'], r['firstAired'], r['id'],)
						try:
							cursor.execute(qry, qargs)
							g.conn.commit()
						except psycopg2.DatabaseError:
							g.conn.rollback()
							cursor.close()
							raise
					else:
						print('%s episode %s is not new' % (s['name'], r['id']))
						episode = cursor.fetchone()
						if episode['name'] != r['episodeName'] or episode['airdate'] != r['firstAired']:
							print('%s episode %s (%s) has a different name than %s (%s)' % (s['name'], episode['name'], episode['airdate'], r['episodeName'], r['firstAired']))
							try:
								cursor.execute("""UPDATE episode SET name = %s, airdate = (%s::DATE + '1 day'::INTERVAL) WHERE id = %s""", (r['episodeName'], r['firstAired'], episode['id'],))
								g.conn.commit()
							except psycopg2.DatabaseError:
								g.conn.rollback()
								cursor.close()
								raise
	cursor.close
	return jsonify(error=error)


@schedule.route('/shows/list', methods=['GET'])
@login_required
def shows_list():
	cursor = g.conn.cursor()
	cursor.execute("""SELECT * FROM tvshow WHERE follows_tvshow(%s, id) ORDER BY name ASC""", (session['userid'],))
	tvshows = query_to_dict_list(cursor)
	cursor.close()
	for s in tvshows:
		s['poster'] = tvdb.get_poster(s['tvdb_id'])
	return render_template('shows.html', tvshows=tvshows)


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


@schedule.route('/movies/list', methods=['GET'])
@login_required
def movies_list():
	cursor = g.conn.cursor()
	qry = """SELECT m.*,
				to_char(m.releasedate, 'Day DD/MM/YYYY') AS releasedate_str, 
				m.releasedate < current_date AS in_past 
			FROM movie m
			WHERE follows_movie(%s, m.id) 
			ORDER BY m.releasedate, m.name"""
	cursor.execute(qry, (session['userid'],))
	movies = query_to_dict_list(cursor)
	cursor.close()
	outstanding = any(m['in_past'] is True for m in movies)
	dates = []
	for m in movies:
		if m['in_past'] is False and m['releasedate_str'] not in dates:
			dates.append(e['releasedate_str'])
		m['poster'] = moviedb.get_poster(m['moviedb_id'])
	return render_template('movies.html', outstanding=outstanding, dates=dates, movies=movies)


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
			year = datetime.datetime.strptime(r['firstAired'], '%Y-%m-%d').year if r['firstAired'] else None
			result.append({ 'id':r['id'], 'name':r['seriesName'], 'poster':r['banner'], 'year':year })
	return jsonify(error=error, result=result)


@schedule.route('/movies/follow', methods=['POST'])
@login_required
def movies_follow():
	error = None
	params = params_to_dict(request.form)
	moviedb_id = params.get('moviedb_id')
	name = params.get('name')
	if moviedb_id and name:
		cursor = g.conn.cursor()
		cursor.execute("""SELECT * FROM movie WHERE moviedb_id = %s""", (moviedb_id,))
		if cursor.rowcount <= 0:
			cursor.execute("""INSERT INTO movie (name, releasedate, moviedb_id) VALUES (%s, %s, %s) RETURNING id""", (name, moviedb_id,))
		movieid = query_to_dict_list(cursor)[0]['id']
		tvdb.get_poster(moviedb_id)
		# Only add link if one doesn't already exist
		cursor.execute("""SELECT add_watcher_movie(%s, %s)""", (session['userid'], movieid,))
		g.conn.commit()
		cursor.close()
	else:
		error = 'Please select a show.'
	return jsonify(error=error)
