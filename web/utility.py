
from flask import Flask, request, g, Blueprint, redirect, url_for, session, render_template, flash, jsonify
import json
import requests
import psycopg2, psycopg2.extras
import datetime

def login_required(f):
	def decorated_function(*args, **kwargs):
		if not is_logged_in():
			return redirect(url_for('home.index'))
		return f(*args, **kwargs)
	return decorated_function


def is_logged_in():
	return session.get('userid') is not None
