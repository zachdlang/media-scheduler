
from web.utility import *
from passlib.context import CryptContext
from web.home import home

app = Flask(__name__)

app.config.from_pyfile('site_config.cfg')
app.secret_key = app.config['SECRETKEY']

app.register_blueprint(home, url_prefix='')

app.jinja_env.globals.update(is_logged_in=is_logged_in)


@app.before_request
def before_request():
	if '/static/' in request.path:
		return
	g.conn = psycopg2.connect(database=app.config['DBNAME'], user=app.config['DBUSER'],
			password=app.config['DBPASS'], port=app.config['DBPORT'],
			host=app.config['DBHOST'],
			cursor_factory=psycopg2.extras.DictCursor)
	g.passwd_context = CryptContext().from_path(get_file_location('/passlibconfig.ini'))
	g.config = app.config
