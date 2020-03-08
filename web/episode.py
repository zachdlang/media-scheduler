# Third party imports
from flask import Blueprint, jsonify, Response

# Local imports
from web import tvdb
from flasktools.db import fetch_query, mutate_query
from flasktools.auth.oauth import auth_token_required

bp = Blueprint('episodes', __name__)


@bp.route('/list', methods=['GET'])
@auth_token_required
def getlist(userid: int) -> Response:
	from web.asynchro import fetch_episode_image

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
		fetch_episode_image.delay(e['tvdb_id'])
		e['image'] = tvdb.episode_image(e['tvdb_id'])
		del e['tvdb_id']

	return jsonify(episodes)


@bp.route('/<int:episodeid>', methods=['PUT'])
@auth_token_required
def mark_watched(userid: int, episodeid: int) -> Response:
	mutate_query(
		"SELECT mark_episode_watched(%s, %s)",
		(userid, episodeid,)
	)
	return jsonify()
