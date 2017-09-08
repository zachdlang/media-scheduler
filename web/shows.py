
from web.utility import *
from web import tvdb

shows = Blueprint('shows', __name__)


@shows.route('/schedule', methods=['GET'])
@login_required
def schedule():
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
		e['poster'] = get_show_poster(e['show_tvdb_id'])
	return render_template('schedule.html', outstanding=outstanding, dates=dates, episodes=episodes)


@shows.route('/schedule/watched', methods=['POST'])
@login_required
def schedule_watched():
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


@shows.route('/schedule/update', methods=['GET'])
def schedule_update():
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
					if r['episodeName'] is not None:
						r['episodeName'] = strip_unicode_characters(r['episodeName'])
						cursor.execute("""SELECT * FROM episode WHERE tvdb_id = %s""", (r['id'],))
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
							if episode['name'] != r['episodeName']:
								print('%s episode %s has a different name than %s' % (s['name'], episode['name'], r['episodeName']))
								try:
									cursor.execute("""UPDATE episode SET name = %s WHERE id = %s""", (r['episodeName'], episode['id'],))
									g.conn.commit()
								except psycopg2.DatabaseError:
									g.conn.rollback()
									cursor.close()
									raise
					else:
						print('%s episode %s has no name' % (s['name'], r['id']))
	cursor.close
	return jsonify(error=error)


@shows.route('/list', methods=['GET'])
@login_required
def list():
	cursor = g.conn.cursor()
	cursor.execute("""SELECT * FROM tvshow WHERE follows_tvshow(%s, id) ORDER BY name ASC""", (session['userid'],))
	tvshows = query_to_dict_list(cursor)
	cursor.close()
	for s in tvshows:
		s['poster'] = get_show_poster(s['tvdb_id'])
	return render_template('shows.html', tvshows=tvshows)


@shows.route('/search', methods=['GET'])
@login_required
def search():
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


@shows.route('/follow', methods=['POST'])
@login_required
def follow():
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
		fetch_poster(tvdb_id)
		# Only add link if one doesn't already exist
		cursor.execute("""SELECT add_watcher_tvshow(%s, %s)""", (session['userid'], tvshowid,))
		g.conn.commit()
		cursor.close()
	else:
		error = 'Please select a show.'
	return jsonify(error=error)


@shows.route('/unfollow', methods=['POST'])
@login_required
def unfollow():
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


def get_show_poster(tvdb_id):
	fetch_poster(tvdb_id)
	return url_for('static', filename='images/poster_%s.jpg' % tvdb_id)


def fetch_poster(tvdb_id):
	if not os.path.exists(get_file_location('/static/images/poster_%s.jpg' % tvdb_id)):
		resp = tvdb.image_search(tvdb_id)
		if len(resp) > 0:
			top_poster = resp[0]
			for r in resp:
				if r['ratingsInfo']['average'] > top_poster['ratingsInfo']['average']:
					top_poster = r
		urlretrieve('http://thetvdb.com/banners/%s' % top_poster['fileName'], get_file_location('/static/images/poster_%s.jpg' % tvdb_id))
		img = Image.open(get_file_location('/static/images/poster_%s.jpg' % tvdb_id))
		img_scaled = img.resize((int(img.size[0]/2),int(img.size[1]/2)), Image.ANTIALIAS)
		img_scaled.save(get_file_location('/static/images/poster_%s.jpg' % tvdb_id), optimize=True, quality=95)
