# Standard library imports
import os
from functools import wraps
from collections import OrderedDict

# Third party imports
from flask import session, redirect, url_for


class SchedulerException(Exception):
	pass


def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if not is_logged_in():
			return redirect(url_for('schedule.login'))
		return f(*args, **kwargs)

	return decorated_function


def is_logged_in():
	return session.get('userid') is not None


def params_to_dict(request_params):
	d = request_params.to_dict()
	for key, value in d.items():
		if isinstance(value, str):
			value = value.strip()
		if value == '':
			d[key] = None
	return d


def query_to_dict_list(cursor):
	d = []
	for row in cursor.fetchall():
		r = OrderedDict()
		for (attr, val) in zip((d[0] for d in cursor.description), row):
			if val == '':
				val = None
			r[str(attr)] = val
		d.append(r)
	return d


def get_file_location(filename):
	return os.path.dirname(os.path.abspath(__file__)) + filename


def strip_unicode_characters(s):
	replacements = {'’': "'"}
	for key, value in replacements.items():
		s = s.replace(key, value)
	return s.encode('ascii', 'ignore').decode('ascii')
