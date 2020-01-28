#!/usr/bin/env python3
from web import app

import os
from flask_cors import CORS

extra_dirs = ['web/templates']
extra_files = []
for extra_dir in extra_dirs:
	for dirname, dirs, files in os.walk(extra_dir):
		for filename in files:
			filename = os.path.join(dirname, filename)
			if os.path.isfile(filename):
				extra_files.append(filename)

CORS(app, resources={r'/*': {'origins': '*'}})

app.run(debug=True, port=8000, extra_files=extra_files)
