
from web.utility import *
from web import tvdb

home = Blueprint('home', __name__)


@home.route('/', methods=['GET'])
def index():
	return redirect(url_for('home.login'))


@home.route('/login', methods=['GET','POST'])
def login():
	check_for_episodes()
	if is_logged_in():
		return redirect(url_for('home.schedule'))

	if request.method == 'POST':
		pass

	return render_template('login.html')


@home.route('/schedule', methods=['GET'])
@login_required
def schedule():
	return render_template('schedule.html')


def check_for_episodes():
	# minus 1 day to account for US airdates compared to NZ airdates
	airdate = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
	cursor = g.conn.cursor()
	cursor.execute("""SELECT * FROM tvshow""")
	shows = cursor.fetchall()
	for s in shows:
		print('Checking for %s episodes for %s' % (airdate, s['name']))
		resp = tvdb.episode_search(s['tvdb_id'], airdate)
		if resp:
			for r in resp:
				cursor.execute("""SELECT * FROM episode WHERE tvdb_id = %s""", (r['id'],))
				if cursor.rowcount <= 0:
					print('Adding new episode...')
					qry = """INSERT INTO episode (tvshowid, seasonnumber, episodenumber, name, airdate, tvdb_id) VALUES (%s, %s, %s, %s, %s, %s)"""
					qargs = (s['id'], r['airedSeason'], r['airedEpisodeNumber'], r['episodeName'], r['firstAired'], r['id'],)
					cursor.execute(qry, qargs)
				else:
					print('Skipping existing episode...')
	g.conn.commit()
	cursor.close()


def import_showlist():
	cursor = g.conn.cursor()
	with open('showlist.txt') as f:
		lines = f.readlines()
	for line in lines:
		# Remove any newline characters
		line = line.strip()
		cursor.execute("""SELECT * FROM tvshow WHERE TRIM(LOWER(name)) = TRIM(LOWER(%s))""", (line,))
		if cursor.rowcount > 0:
			print('Skipping already existing %s' % line)
			continue
		print(line)
		print(cursor.fetchall())
		resp = tvdb.series_search(line)
		for s in resp:
			print('%s has ID %s' % (s['seriesName'], s['id']))

		for i in range(0, len(resp)):
			print('(%s) %s' % (i+1, resp[i]['seriesName']))
		choice = input('Select correct series for %s ("i" to ignore): ' % (line,))
		if choice == '':
			tvdb_id = resp[0]['id']
		elif choice == 'i':
			continue
		elif int(choice) < 1 or int(choice) > len(resp):
			cursor.close()
			raise Exception('Invalid input.')
		else:
			tvdb_id = resp[int(choice)-1]['id']
		cursor.execute("""INSERT INTO tvshow (name, tvdb_id) VALUES (%s, %s)""", (line, tvdb_id,))
	g.conn.commit()
	cursor.close()
