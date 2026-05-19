import os
import json
import requests
from datetime import datetime, timezone

CLIENT_ID     = os.environ['WHOOP_CLIENT_ID'].strip()
CLIENT_SECRET = os.environ['WHOOP_CLIENT_SECRET'].strip()
REFRESH_TOKEN = os.environ['WHOOP_REFRESH_TOKEN'].strip()

print(f"Client ID length: {len(CLIENT_ID)}")
print(f"Refresh token length: {len(REFRESH_TOKEN)}")

# ── Get access token ──
r = requests.post(
    'https://api.prod.whoop.com/oauth/oauth2/token',
    data={
        'grant_type':    'refresh_token',
        'refresh_token': REFRESH_TOKEN,
        'client_id':     CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
)
print(f"Token status: {r.status_code}")
print(f"Token body: {r.text}")
r.raise_for_status()
access_token = r.json()['access_token']

headers = {'Authorization': 'Bearer ' + access_token}

# ── Fetch latest recovery ──
rec_resp = requests.get(
    'https://api.prod.whoop.com/developer/v1/recovery?limit=1',
    headers=headers
)
print(f"Recovery status: {rec_resp.status_code}")
print(f"Recovery body: {rec_resp.text}")
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

print(f"Updated: recovery={recovery_pct}% HRV={hrv}ms RHR={rhr}bpm sleep={sleep_score}% strain={strain}")
