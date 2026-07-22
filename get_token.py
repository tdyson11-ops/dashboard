"""
Run once to get your WHOOP refresh token.
Usage: python get_token.py <CLIENT_ID> <CLIENT_SECRET>
"""
import sys
import json
import secrets
import urllib.parse
import requests

CLIENT_ID     = sys.argv[1]
CLIENT_SECRET = sys.argv[2]
REDIRECT_URI  = 'http://localhost:8080/callback'
SCOPE         = 'offline read:recovery read:cycles read:sleep'
STATE         = secrets.token_hex(16)

auth_url = (
    'https://api.prod.whoop.com/oauth/oauth2/auth'
    '?response_type=code'
    '&client_id=' + urllib.parse.quote(CLIENT_ID) +
    '&redirect_uri=' + urllib.parse.quote(REDIRECT_URI) +
    '&scope=' + urllib.parse.quote(SCOPE) +
    '&state=' + STATE
)

print('\nOpen this URL in your browser and log in with WHOOP:\n')
print(auth_url)
print('\nAfter authorising, your browser will show ERR_CONNECTION_REFUSED.')
print('Copy the full URL from the address bar and paste it here:\n')

redirect_url = input('Paste URL: ').strip()

parsed = urllib.parse.urlparse(redirect_url)
params = urllib.parse.parse_qs(parsed.query)

if 'code' not in params:
    print('No code found in that URL. Make sure you copied the full address bar URL.')
    sys.exit(1)

code = params['code'][0]

# Exchange code for tokens
r = requests.post(
    'https://api.prod.whoop.com/oauth/oauth2/token',
    data={
        'grant_type':    'authorization_code',
        'code':          code,
        'client_id':     CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri':  REDIRECT_URI,
    }
)

if not r.ok:
    print(f'\nError {r.status_code}: {r.text}')
    sys.exit(1)

tokens = r.json()

print('\n=== SUCCESS ===')
print('Add this as a GitHub secret named WHOOP_REFRESH_TOKEN:')
print()
print(tokens['refresh_token'])
print()
