import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

CLIENT_ID     = os.environ['WHOOP_CLIENT_ID']
CLIENT_SECRET = os.environ['WHOOP_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['WHOOP_REFRESH_TOKEN']


def post(url, data, headers=None):
    body = urllib.parse.urlencode(data).encode()
    req  = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get(url, token):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# ── Get access token ──
tokens = post(
    'https://api.prod.whoop.com/oauth/oauth2/token',
    {
        'grant_type':    'refresh_token',
        'refresh_token': REFRESH_TOKEN,
        'client_id':     CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope':         'offline read:recovery read:cycles read:sleep read:body_measurement',
    }
)
access_token = tokens['access_token']

# ── Fetch latest recovery ──
recovery_data = get(
    'https://api.prod.whoop.com/developer/v1/recovery?limit=1',
    access_token
)

rec = recovery_data['records'][0]
score = rec['score']

recovery_pct = round(score['recovery_score'])
hrv          = round(score['hrv_rmssd_milli'])
rhr          = round(score['resting_heart_rate'])

# ── Fetch latest sleep ──
sleep_data = get(
    'https://api.prod.whoop.com/developer/v1/activity/sleep?limit=1',
    access_token
)
sleep_score = round(sleep_data['records'][0]['score']['sleep_performance_percentage']) \
    if sleep_data['records'] else 0

# ── Fetch latest cycle (strain) ──
cycle_data = get(
    'https://api.prod.whoop.com/developer/v1/cycle?limit=1',
    access_token
)
strain = round(cycle_data['records'][0]['score']['strain'], 1) \
    if cycle_data['records'] and cycle_data['records'][0].get('score') else 0.0

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

print(f"Updated: recovery={recovery_pct}% HRV={hrv}ms RHR={rhr}bpm sleep={sleep_score}% strain={strain}")
