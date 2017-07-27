
from flask import Flask, request, g, Blueprint, redirect, url_for, session, render_template, flash, jsonify
from functools import wraps
import json
import requests
from urllib.request import urlretrieve
from PIL import Image
import psycopg2, psycopg2.extras
import datetime
import os


def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if not is_logged_in():
			return redirect(url_for('home.index'))
		return f(*args, **kwargs)

	return decorated_function


def is_logged_in():
	return session.get('userid') is not None


def params_to_dict(request_params):
	d = request_params.to_dict()
	for key, value in d.items():
		if value == '':
			d[key] = None
	return d

def get_file_location(filename):
	return os.path.dirname(os.path.abspath(__file__)) + filename
