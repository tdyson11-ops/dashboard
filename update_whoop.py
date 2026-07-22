import os
import sys
import json
import base64
import hashlib
import requests
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken

CLIENT_ID     = os.environ['WHOOP_CLIENT_ID'].strip()
CLIENT_SECRET = os.environ['WHOOP_CLIENT_SECRET'].strip()
SEED_TOKEN    = os.environ.get('WHOOP_REFRESH_TOKEN', '').strip()
TOKEN_KEY     = os.environ.get('WHOOP_TOKEN_KEY', '').strip()

# WHOOP refresh tokens are single-use: every refresh returns a new one and
# invalidates the old one. The GitHub secret only seeds the very first run;
# after that the current token lives in TOKEN_FILE, encrypted with
# WHOOP_TOKEN_KEY, and is committed back to the repo by the workflow.
TOKEN_FILE = '.whoop_token.enc'


def fernet():
    digest = hashlib.sha256(TOKEN_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def load_rotated_token():
    if not TOKEN_KEY or not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, 'rb') as f:
            return fernet().decrypt(f.read()).decode()
    except (InvalidToken, ValueError):
        print('Could not decrypt ' + TOKEN_FILE + ' (key changed?) — falling back to seed secret')
        return None


def save_rotated_token(token):
    if not TOKEN_KEY:
        print('WARNING: WHOOP_TOKEN_KEY secret not set — cannot persist the rotated '
              'refresh token. The next run WILL fail because WHOOP refresh tokens are '
              'single-use. Add a WHOOP_TOKEN_KEY secret (any long random string).')
        return
    with open(TOKEN_FILE, 'wb') as f:
        f.write(fernet().encrypt(token.encode()))
    print('Rotated refresh token saved to ' + TOKEN_FILE)


def request_tokens(refresh_token):
    # scope=offline is required by WHOOP on refresh; omitting it returns
    # 400 invalid_request ("request is malformed").
    r = requests.post(
        'https://api.prod.whoop.com/oauth/oauth2/token',
        data={
            'grant_type':    'refresh_token',
            'refresh_token': refresh_token,
            'client_id':     CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'scope':         'offline',
        }
    )
    print(f'Token status: {r.status_code}')
    if not r.ok:
        print(f'Token body: {r.text}')
    return r


# ── Get access token: try the rotated token first, then the seed secret ──
resp = None
for source, token in (('rotated', load_rotated_token()), ('seed secret', SEED_TOKEN)):
    if not token:
        continue
    print(f'Trying {source} refresh token (length {len(token)})')
    resp = request_tokens(token)
    if resp.ok:
        break

if resp is None or not resp.ok:
    print('\nAll refresh tokens rejected. Re-authorise with WHOOP:')
    print('  1. python get_token.py <CLIENT_ID> <CLIENT_SECRET>')
    print('  2. Update the WHOOP_REFRESH_TOKEN repo secret with the new token')
    print('  3. Delete ' + TOKEN_FILE + ' from the repo if it exists')
    sys.exit(1)

tokens = resp.json()
access_token = tokens['access_token']
if tokens.get('refresh_token'):
    save_rotated_token(tokens['refresh_token'])

headers = {'Authorization': 'Bearer ' + access_token}

# ── Fetch latest recovery ──
rec_resp = requests.get(
    'https://api.prod.whoop.com/developer/v1/recovery?limit=1',
    headers=headers
)
print(f'Recovery status: {rec_resp.status_code}')
rec_resp.raise_for_status()
rec_data = rec_resp.json()

score        = rec_data['records'][0]['score']
recovery_pct = round(score['recovery_score'])
hrv          = round(score['hrv_rmssd_milli'])
rhr          = round(score['resting_heart_rate'])

# ── Fetch latest sleep ──
sleep_data = requests.get(
    'https://api.prod.whoop.com/developer/v1/activity/sleep?limit=1',
    headers=headers
).json()
sleep_score = round(sleep_data['records'][0]['score']['sleep_performance_percentage']) \
    if sleep_data.get('records') else 0

# ── Fetch latest cycle (strain) ──
cycle_data = requests.get(
    'https://api.prod.whoop.com/developer/v1/cycle?limit=1',
    headers=headers
).json()
strain = round(cycle_data['records'][0]['score']['strain'], 1) \
    if cycle_data.get('records') and cycle_data['records'][0].get('score') else 0.0

# ── Update data.json ──
with open('data.json', 'r') as f:
    data = json.load(f)

data['whoop'] = {
    'recovery':    recovery_pct,
    'hrv':         hrv,
    'rhr':         rhr,
    'sleep_score': sleep_score,
    'strain':      strain,
}

today = datetime.now(timezone.utc)
data['updated'] = today.strftime('%-d %B %Y')

with open('data.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f'Updated: recovery={recovery_pct}% HRV={hrv}ms RHR={rhr}bpm sleep={sleep_score}% strain={strain}')
