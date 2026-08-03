"""
End-to-end test of update_whoop.py with a fully mocked WHOOP API.
Proves: scope=offline is sent, single-use token rotation is persisted and
re-read on the next run, and data.json is written correctly.

Requires `requests` and `cryptography`:
    python -m venv venv && venv/bin/pip install requests cryptography
    venv/bin/python test_whoop.py
"""
import os, sys, json, base64, hashlib, shutil, tempfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = tempfile.mkdtemp()
shutil.copy(os.path.join(HERE, 'update_whoop.py'), os.path.join(WORK, 'update_whoop.py'))
# seed a minimal data.json
with open(os.path.join(WORK, 'data.json'), 'w') as f:
    json.dump({"updated": "old", "whoop": {}, "focus": ["x"]}, f)
os.chdir(WORK)

os.environ['WHOOP_CLIENT_ID'] = 'cid'
os.environ['WHOOP_CLIENT_SECRET'] = 'csecret'
os.environ['WHOOP_REFRESH_TOKEN'] = 'SEED_TOKEN_1'
os.environ['WHOOP_TOKEN_KEY'] = 'a-long-random-key-for-testing-123456'

posted = {}

class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)
        self.ok = status < 400
    def json(self): return self._payload
    def raise_for_status(self):
        if not self.ok:
            raise Exception(f'HTTP {self.status_code}')

# Track which refresh tokens the "server" considers valid (single-use semantics)
valid_tokens = {'SEED_TOKEN_1'}
issued = {'count': 0}

def fake_post(url, data=None, **kw):
    posted['url'] = url
    posted['data'] = data
    rt = data.get('refresh_token')
    if rt not in valid_tokens:
        return FakeResp(400, {"error": "invalid_request",
                              "error_description": "malformed"})
    # single-use: invalidate the used token, issue a new one
    valid_tokens.discard(rt)
    issued['count'] += 1
    new_rt = f'ROTATED_TOKEN_{issued["count"]}'
    valid_tokens.add(new_rt)
    return FakeResp(200, {"access_token": "ACCESS_XYZ", "refresh_token": new_rt,
                          "expires_in": 3600})

def fake_get(url, headers=None, **kw):
    assert headers.get('Authorization') == 'Bearer ACCESS_XYZ', 'wrong auth header'
    if 'recovery' in url:
        return FakeResp(200, {"records": [{"score": {
            "recovery_score": 68.4, "hrv_rmssd_milli": 61.2, "resting_heart_rate": 49.7}}]})
    if 'sleep' in url:
        return FakeResp(200, {"records": [{"score": {"sleep_performance_percentage": 82.3}}]})
    if 'cycle' in url:
        return FakeResp(200, {"records": [{"score": {"strain": 11.63}}]})
    return FakeResp(404, {})

def run_script():
    with mock.patch('requests.post', side_effect=fake_post), \
         mock.patch('requests.get', side_effect=fake_get):
        # exec the script fresh each time (it runs at module top level)
        src = open('update_whoop.py').read()
        g = {'__name__': '__main__'}
        try:
            exec(compile(src, 'update_whoop.py', 'exec'), g)
            return 0
        except SystemExit as e:
            return e.code or 0

print('=== RUN 1 (uses seed token) ===')
rc = run_script()
assert rc == 0, f'run 1 exited {rc}'
# scope=offline must be present
assert posted['data'].get('scope') == 'offline', 'scope=offline NOT sent!'
print('scope=offline sent: OK')
# rotated token persisted, encrypted
assert os.path.exists('.whoop_token.enc'), 'token file not written'
digest = hashlib.sha256(os.environ['WHOOP_TOKEN_KEY'].encode()).digest()
from cryptography.fernet import Fernet
fer = Fernet(base64.urlsafe_b64encode(digest))
saved = fer.decrypt(open('.whoop_token.enc', 'rb').read()).decode()
assert saved == 'ROTATED_TOKEN_1', f'expected ROTATED_TOKEN_1, got {saved}'
print(f'rotated token persisted (encrypted): {saved}')
# data.json updated with rounded values
d = json.load(open('data.json'))
metrics = {k: v for k, v in d['whoop'].items() if k != 'fetched_at'}
assert metrics == {"recovery": 68, "hrv": 61, "rhr": 50, "sleep_score": 82, "strain": 11.6}, metrics
# fetched_at drives the dashboard's "today / yesterday" staleness tag
import re
assert re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', d['whoop']['fetched_at']), d['whoop']['fetched_at']
print(f'data.json whoop block: {d["whoop"]}')
assert d['updated'] != 'old', 'updated date not refreshed'
assert d['focus'] == ['x'], 'other data.json fields clobbered!'
print('other data.json fields preserved: OK')

print()
print('=== RUN 2 (seed token now invalid; must use rotated token from file) ===')
# Simulate next day: the SEED token in the secret is now dead (single-use).
# valid_tokens currently holds ROTATED_TOKEN_1 which is in the file.
rc = run_script()
assert rc == 0, f'run 2 exited {rc}'
saved2 = fer.decrypt(open('.whoop_token.enc', 'rb').read()).decode()
assert saved2 == 'ROTATED_TOKEN_2', f'expected ROTATED_TOKEN_2, got {saved2}'
print(f'run 2 used file token and rotated again: {saved2}')
print(f'refresh token sent in run 2: {posted["data"]["refresh_token"]} (should be ROTATED_TOKEN_1)')
assert posted['data']['refresh_token'] == 'ROTATED_TOKEN_1'

print()
print('=== RUN 3 (all tokens dead -> must exit 1 with guidance, not crash) ===')
valid_tokens.clear()  # kill everything, e.g. token revoked
# also corrupt the file token by clearing valid set; seed already dead
rc = run_script()
assert rc == 1, f'expected clean exit 1, got {rc}'
print('exited cleanly with code 1 when all tokens rejected: OK')

print()
print('ALL WHOOP TESTS PASSED')
shutil.rmtree(WORK, ignore_errors=True)
