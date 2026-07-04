"""The notice board — the single place proactive output lands.

Rules baked in:
- notices are stored before they're shown, so nothing noticed while Tom is
  away is ever lost (catch-up-on-return, never deliver-once-and-lose-it);
- every notice is dismissible;
- a dedupe key stops the same observation nagging on every check run.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from .config import STATE_DIR

NOTICES_PATH = STATE_DIR / "notices.json"

LEVELS = ("notice", "interrupt", "critical")   # calm log → worth interrupting → ignores quiet hours


class NoticeBoard:
    def __init__(self, path: Path | None = None):
        self.path = path or NOTICES_PATH
        self._lock = threading.Lock()   # heartbeat thread and interface share this board

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text())

    def _save(self, notices: list[dict]) -> None:
        self.path.write_text(json.dumps(notices, indent=2) + "\n")

    def add(self, message: str, level: str = "notice", key: str | None = None) -> dict | None:
        """Store a notice. Returns it, or None when the key already exists
        (dismissed or not) — the same observation isn't raised twice."""
        if level not in LEVELS:
            level = "notice"
        with self._lock:
            notices = self._load()
            if key and any(n.get("key") == key for n in notices):
                return None
            notice = {
                "id": max((n["id"] for n in notices), default=0) + 1,
                "message": message,
                "level": level,
                "key": key,
                "created": datetime.now().isoformat(sep=" ", timespec="seconds"),
                "seen": False,
                "dismissed": False,
            }
            notices.append(notice)
            self._save(notices)
            return notice

    def pending(self) -> list[dict]:
        """Everything not yet dismissed — what /notices shows."""
        with self._lock:
            return [n for n in self._load() if not n["dismissed"]]

    def unseen(self) -> list[dict]:
        """Pending notices Tom hasn't been shown yet — the catch-up set."""
        with self._lock:
            return [n for n in self._load() if not n["dismissed"] and not n["seen"]]

    def mark_seen(self, ids: list[int]) -> None:
        with self._lock:
            notices = self._load()
            for n in notices:
                if n["id"] in ids:
                    n["seen"] = True
            self._save(notices)

    def dismiss(self, notice_id: int) -> bool:
        with self._lock:
            notices = self._load()
            for n in notices:
                if n["id"] == notice_id and not n["dismissed"]:
                    n["dismissed"] = True
                    self._save(notices)
                    return True
            return False
