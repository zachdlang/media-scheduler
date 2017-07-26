
import json
import requests

TVDB = 'https://api.thetvdb.com'
config = {}

def login():
	print('Logging in...')
	data = { 'apikey':config['TVDB_APIKEY'], 'userkey':config['TVDB_USERKEY'], 'username':config['TVDB_USERNAME'] }
	headers = { 'content-type':'application/json' }
	r = requests.post(TVDB+'/login', data=json.dumps(data), headers=headers).text
	resp = json.loads(r)
	if 'Error' in resp:
		raise Exception(resp['Error'])
	config['TOKEN'] = resp['token']

def search(name):
	print('Searching...')
	params = { 'name':name }
	headers = { 'content-type':'application/json', 'Authorization':'Bearer %s' % config['TOKEN'] }
	r = requests.get(TVDB+'/search/series', params=params, headers=headers).text
	resp = json.loads(r)
	if 'Error' in resp:
		raise Exception(resp['Error'])
	for r in resp['data']:
		print('%s has ID %s' % (r['seriesName'], r['id']))

def main():
	print('Running...')
	with open('config.cfg') as f:
		content = f.readlines()
	for line in content:
		(key, value) = line.replace('\n','').split(' = ')
		config[key] = value

	if not config.get('TOKEN'):
		login()

	search('American Ninja Warrior')



main()