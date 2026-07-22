"""
One-time WHOOP token seeder, run by the "Seed WHOOP Token" GitHub Action.

Takes the authorization code (or the full redirect URL) from a WHOOP login,
exchanges it for a refresh token server-side (GitHub's runners can reach WHOOP),
and writes it encrypted to .whoop_token.enc so the daily sync can use it.
"""
import os
import sys
import base64
import hashlib
import urllib.parse
import requests
from cryptography.fernet import Fernet

CLIENT_ID     = os.environ['WHOOP_CLIENT_ID'].strip()
CLIENT_SECRET = os.environ['WHOOP_CLIENT_SECRET'].strip()
TOKEN_KEY     = os.environ['WHOOP_TOKEN_KEY'].strip()
RAW           = os.environ['WHOOP_CODE'].strip()
REDIRECT      = 'http://localhost:8080/callback'  # must match the login request

# Accept either a bare code or the whole "http://localhost:8080/callback?code=..." URL
if 'code=' in RAW:
    query = urllib.parse.urlparse(RAW).query or RAW.split('?', 1)[-1]
    code = urllib.parse.parse_qs(query).get('code', [''])[0]
else:
    code = RAW

if not code:
    print('No authorization code found in the input. Paste the code (or the full '
          'localhost callback URL) from the WHOOP login redirect.')
    sys.exit(1)

r = requests.post(
    'https://api.prod.whoop.com/oauth/oauth2/token',
    data={
        'grant_type':    'authorization_code',
        'code':          code,
        'client_id':     CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri':  REDIRECT,
    }
)
print('Exchange status:', r.status_code)
if not r.ok:
    print('Body:', r.text)
    print('\nThe code has likely expired (they last about a minute) or was already used.')
    print('Click the WHOOP login link again for a FRESH code, then re-run this workflow.')
    sys.exit(1)

refresh_token = r.json().get('refresh_token')
if not refresh_token:
    print('No refresh_token in response — was the "offline" scope included in the login?')
    print('Response keys:', list(r.json().keys()))
    sys.exit(1)

digest = hashlib.sha256(TOKEN_KEY.encode()).digest()
fernet = Fernet(base64.urlsafe_b64encode(digest))
with open('.whoop_token.enc', 'wb') as f:
    f.write(fernet.encrypt(refresh_token.encode()))

# sanity: prove it decrypts back
assert fernet.decrypt(open('.whoop_token.enc', 'rb').read()).decode() == refresh_token
print('Success: refresh token seeded (length %d) and encrypted to .whoop_token.enc' % len(refresh_token))
