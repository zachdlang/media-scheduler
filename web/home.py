
from web.utility import *

home = Blueprint('home', __name__)


@home.route('/', methods=['GET'])
def index():
	return redirect(url_for('home.login'))


@home.route('/login', methods=['GET','POST'])
def login():
	if is_logged_in():
		return redirect(url_for('schedule.shows'))

	if request.method == 'POST':
		params = params_to_dict(request.form)
		cursor = g.conn.cursor()
		cursor.execute("""SELECT * FROM watcher WHERE TRIM(username) = TRIM(%s)""", (params['username'],))
		resp = query_to_dict_list(cursor)[0]
		ok, new_hash = g.passwd_context.verify_and_update(params['password'].strip(), resp['password'].strip())
		if ok:
			if new_hash:
				cursor.execute("""UPDATE watcher SET password = %s WHERE id = %s""", (new_hash, resp['id'],))
				g.conn.commit()
			session.new = True
			session.permanent = True
			session['userid'] = resp['id']
		cursor.close()
			
		if ok:
			return redirect(url_for('schedule.shows'))
		else:
			flash('Login failed.', 'danger')
			return redirect(url_for('home.index'))

	return render_template('login.html')


@home.route('/logout', methods=['GET'])
def logout():
	session.pop('userid', None)
	return redirect(url_for('home.index'))
