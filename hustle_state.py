#!/usr/bin/env python3
"""
Read the app state your phone already syncs to Firestore.

The pipeline counters live in localStorage so they stay a single tap to
update. sync.js mirrors them to Firestore, which means a scheduled job can
read them too — no need to move them into the repo and lose the tapping.

Needs two secrets: FIREBASE_EMAIL and FIREBASE_PASSWORD, the same ones you
use on the sync bar. The project id and web API key are read straight out of
sync.js, so there's one source of truth for them.

    python3 hustle_state.py        # prints what it can see, for debugging
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SYNC_JS = ROOT / "sync.js"

IDENTITY = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
FIRESTORE = "https://firestore.googleapis.com/v1"


def firebase_config():
    """Pull apiKey / projectId out of sync.js so they're not duplicated here."""
    api_key = os.environ.get("FIREBASE_API_KEY", "")
    project = os.environ.get("FIREBASE_PROJECT_ID", "")
    if api_key and project:
        return api_key, project
    try:
        js = SYNC_JS.read_text(encoding="utf-8")
    except OSError:
        return api_key, project
    if not api_key:
        m = re.search(r'apiKey:\s*"([^"]+)"', js)
        api_key = m.group(1) if m else ""
    if not project:
        m = re.search(r'projectId:\s*"([^"]+)"', js)
        project = m.group(1) if m else ""
    return api_key, project


def post_json(url, body, headers=None):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sign_in(api_key, email, password):
    """Returns (id_token, uid)."""
    out = post_json(f"{IDENTITY}?key={api_key}", {
        "email": email, "password": password, "returnSecureToken": True,
    })
    return out["idToken"], out["localId"]


def unwrap(value):
    """Firestore REST wraps every value in a type tag. Unwrap the ones we use."""
    if "stringValue" in value:
        return value["stringValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "booleanValue" in value:
        return value["booleanValue"]
    if "mapValue" in value:
        return {k: unwrap(v) for k, v in value["mapValue"].get("fields", {}).items()}
    if "arrayValue" in value:
        return [unwrap(v) for v in value["arrayValue"].get("values", [])]
    return None


def fetch(key="hustle-state-v1"):
    """The parsed contents of one synced localStorage key, or None."""
    email = os.environ.get("FIREBASE_EMAIL", "").strip()
    password = os.environ.get("FIREBASE_PASSWORD", "")
    if not (email and password):
        return None

    api_key, project = firebase_config()
    if not (api_key and project):
        print("  could not read Firebase config from sync.js", file=sys.stderr)
        return None

    try:
        token, uid = sign_in(api_key, email, password)
        doc = get_json(
            f"{FIRESTORE}/projects/{project}/databases/(default)/documents"
            f"/users/{uid}/state/v1",
            {"Authorization": f"Bearer {token}"},
        )
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        print(f"  Firestore read failed ({e.code}): {body}", file=sys.stderr)
        return None
    except (urllib.error.URLError, OSError, KeyError, ValueError) as e:
        print(f"  Firestore read failed: {e}", file=sys.stderr)
        return None

    data = unwrap(doc.get("fields", {}).get("data", {})) or {}
    raw = data.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def fetch_pipeline():
    """Just the pipeline counters, as a plain dict of ints."""
    state = fetch()
    if not state:
        return None
    pipeline = state.get("pipeline")
    if not isinstance(pipeline, dict):
        return None
    return {k: int(v or 0) for k, v in pipeline.items()}


if __name__ == "__main__":
    key, project = firebase_config()
    print(f"project: {project or '(not found)'}  apiKey: {'set' if key else '(not found)'}")
    print(f"credentials: {'set' if os.environ.get('FIREBASE_EMAIL') else 'not set'}")
    print("pipeline:", json.dumps(fetch_pipeline(), indent=2))
