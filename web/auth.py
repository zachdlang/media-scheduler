from flask import Blueprint, request, jsonify

from flasktools import params_to_dict
from flasktools.auth import authenticate_user
from flasktools.auth.oauth import generate_auth_token


bp = Blueprint('auth', __name__)


@bp.route('', methods=['POST'])
def login():
	params = params_to_dict(request.json)

	userid = authenticate_user(params.get('username'), params.get('password'))
	if userid:
		return jsonify(generate_auth_token(userid))

	return jsonify('Login unsuccessful.'), 401
