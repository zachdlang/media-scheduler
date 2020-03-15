# Third party imports
from flask import Blueprint, jsonify, Response

# Local imports
from web import moviedb
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
			s.moviedb_id AS show_moviedb_id,
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
		fetch_episode_image.delay(
			e['show_moviedb_id'],
			e['seasonnumber'],
			e['episodenumber']
		)
		e['image'] = moviedb.get_episode_static(
			e['show_moviedb_id'],
			e['seasonnumber'],
			e['episodenumber']
		)
		print(e['image'])
		del e['show_moviedb_id']

	return jsonify(episodes)


@bp.route('/<int:episodeid>', methods=['PUT'])
@auth_token_required
def mark_watched(userid: int, episodeid: int) -> Response:
	mutate_query(
		"SELECT mark_episode_watched(%s, %s)",
		(userid, episodeid,)
	)
	return jsonify()
