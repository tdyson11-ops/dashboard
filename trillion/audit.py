"""The audit trail: a plain JSONL file of what Trillion did and why —
tool runs, gate decisions, model calls with running cost, surfaced notices.
When something surprises you, state/audit.jsonl is how you find out what
happened. One JSON object per line; open it in anything."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from .config import STATE_DIR

AUDIT_PATH = STATE_DIR / "audit.jsonl"


class Audit:
    def __init__(self, path: Path | None = None):
        self.path = path or AUDIT_PATH
        self._lock = threading.Lock()

    def log(self, event: str, **fields) -> None:
        entry = {"ts": datetime.now().isoformat(sep=" ", timespec="seconds"), "event": event}
        entry.update(fields)
        with self._lock:
            with open(self.path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")

    def tail(self, n: int = 20) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text().splitlines()[-n:]
        return [json.loads(line) for line in lines]
