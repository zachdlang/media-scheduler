# Standard library imports
from datetime import datetime, time

# Third party imports
from flask import Blueprint, jsonify, Response
import pytz

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
			s.country,
			e.airdate
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
		if e['country'] is not None:
			# Convert to user timezone
			tz = pytz.timezone(pytz.country_timezones[e['country']][0])
			# Hardcode at 8PM, as moviedb doesn't store airtimes
			dt = datetime.combine(e['airdate'], time(20))
			localized = tz.localize(dt)
			# TODO: pull this from user config
			e['airdate'] = localized.astimezone(pytz.timezone('Pacific/Auckland'))

		e['in_past'] = e['airdate'].date() < datetime.today().date()
		# TODO: pull this from user config
		e['airdate'] = datetime.strftime(e['airdate'], '%A %d/%m/%Y')

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
