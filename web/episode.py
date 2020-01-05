# Third party imports
from flask import Blueprint, jsonify

# Local imports
from web import tvdb
from flasktools.db import fetch_query
from flasktools.auth.oauth import auth_token_required, generate_auth_token

bp = Blueprint('episodes', __name__)


# TODO: Replace this with usage of auth_token_required
def test_token_required(f):
	from functools import wraps
	@wraps(f)
	def decorated_function(*args, **kwargs):
		return f(1, *args, **kwargs)

	return decorated_function


@bp.route('/list', methods=['GET'])
# @auth_token_required
@test_token_required
def getlist(userid):
	episodes = fetch_query(
		"""
		SELECT
			e.id,
			e.seasonnumber,
			e.episodenumber,
			e.name,
			e.tvdb_id AS tvdb_id,
			s.name AS show_name,
			to_char(e.airdate, 'Day DD/MM/YYYY') AS airdate_str
		FROM
			episode e
		LEFT JOIN
			tvshow s ON (s.id = e.tvshowid)
		WHERE
			follows_episode(%s, e.id)
		ORDER BY
			e.airdate,
			show_name,
			e.seasonnumber,
			e.episodenumber
		""",
		(userid,)
	)
	for e in episodes:
		tvdb.fetch_episode_image.delay(e['tvdb_id'])
		e['image'] = tvdb.episode_image(e['tvdb_id'])
		del e['tvdb_id']

	return jsonify(episodes)
