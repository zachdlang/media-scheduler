
from web.utility import *
from web.home import home

app = Flask(__name__)

app.config.from_pyfile('site_config.cfg')
app.secret_key = app.config['SECRETKEY']

app.register_blueprint(home, url_prefix='')


@app.before_request
def before_request():
	if '/static/' in request.path:
		return
	g.conn = psycopg2.connect(database=app.config['DBNAME'], user=app.config['DBUSER'],
			password=app.config['DBPASS'], port=app.config['DBPORT'],
			host=app.config['DBHOST'],
			cursor_factory=psycopg2.extras.DictCursor)
	g.config = app.config
