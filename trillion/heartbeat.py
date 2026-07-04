"""The heartbeat — Trillion acting without being spoken to, quietly.

A background thread wakes on an interval and runs the checks configured in
trillion.toml. Most runs produce nothing. Anything noteworthy becomes a
notice on the NoticeBoard (held until seen, dismissible); only interrupt/
critical-level notices outside quiet hours are pushed at Tom immediately.

Durability rules:
- each check's next-due time persists in state/schedule.json, so a restart
  resumes the schedule instead of refiring everything;
- checks run sequentially in the one heartbeat thread, so runs can never
  stack (a slow check delays the loop, it doesn't pile up);
- the loop never blocks on a human: nothing here waits for input, and any
  gated action a check ever triggers falls back to "do nothing + leave a
  note" (see gate.py).

Deliberately self-contained (this file + state/ + config) so moving it to an
always-on machine later is a relocation, not a rewrite.
"""

from __future__ import annotations

import json
import threading
import traceback
from datetime import datetime, time as dtime, timedelta
from pathlib import Path

from .config import ROOT, STATE_DIR

SCHEDULE_PATH = STATE_DIR / "schedule.json"
ERROR_LOG = STATE_DIR / "heartbeat_errors.log"


# --- check implementations ---------------------------------------------------
# Each takes (check_config, config, now) and returns a list of
# (message, dedupe_key) tuples. Empty list = nothing noteworthy (the norm).

def check_reminder_due(check: dict, config, now: datetime) -> list[tuple[str, str]]:
    from .tools.focus import _load_reminders, _save_reminders

    reminders = _load_reminders()
    fired = []
    for r in reminders:
        if r["done"]:
            continue
        if datetime.fromisoformat(r["due"]) <= now:
            fired.append((f"Reminder: {r['text']}", f"reminder-{r['id']}"))
            r["done"] = True   # delivered to the board; the board holds it until dismissed
    if fired:
        _save_reminders(reminders)
    return fired


def check_deadline_approaching(check: dict, config, now: datetime) -> list[tuple[str, str]]:
    data = json.loads((ROOT / "data.json").read_text())
    uni = data.get("university", {})
    deadline_str = uni.get("next_deadline")
    if not deadline_str:
        return []
    deadline = datetime.fromisoformat(deadline_str).date()
    days_left = (deadline - now.date()).days
    if 0 <= days_left <= check.get("days_ahead", 3):
        when = "today" if days_left == 0 else f"in {days_left} day{'s' if days_left != 1 else ''}"
        return [(
            f"University deadline {when} ({deadline_str}): {uni.get('deadline_label', 'deadline')} "
            f"for {uni.get('module', 'your module')}.",
            f"uni-deadline-{deadline_str}",
        )]
    return []


def check_whoop_recovery_low(check: dict, config, now: datetime) -> list[tuple[str, str]]:
    data = json.loads((ROOT / "data.json").read_text())
    recovery = data.get("whoop", {}).get("recovery")
    threshold = check.get("threshold", 40)
    if recovery is not None and recovery <= threshold:
        return [(
            f"WHOOP recovery is low today: {recovery}% (threshold {threshold}%). Go easy.",
            f"whoop-low-{data.get('updated')}-{recovery}",
        )]
    return []


def check_file_exists(check: dict, config, now: datetime) -> list[tuple[str, str]]:
    """A check Tom can trigger on purpose to watch the heartbeat work."""
    path = ROOT / check.get("path", "state/trigger.txt")
    if path.exists():
        mtime = int(path.stat().st_mtime)
        return [(f"Trigger file noticed: {path.name}", f"file-{path.name}-{mtime}")]
    return []


CHECK_TYPES = {
    "reminder_due": check_reminder_due,
    "deadline_approaching": check_deadline_approaching,
    "whoop_recovery_low": check_whoop_recovery_low,
    "file_exists": check_file_exists,
}


# --- quiet hours -------------------------------------------------------------

def in_quiet_hours(now: datetime, start: str | None, end: str | None) -> bool:
    if not start or not end:
        return False
    t = now.time()
    start_t = dtime.fromisoformat(start)
    end_t = dtime.fromisoformat(end)
    if start_t <= end_t:
        return start_t <= t < end_t
    return t >= start_t or t < end_t   # window spans midnight


# --- the heartbeat -----------------------------------------------------------

class Heartbeat:
    def __init__(self, config, board, schedule_path: Path | None = None,
                 on_interrupt=None):
        self.config = config
        self.board = board
        self.schedule_path = schedule_path or SCHEDULE_PATH
        self.on_interrupt = on_interrupt   # interface hook: push a notice at Tom now
        self.checks = [c for c in config.get("heartbeat.checks", []) if c.get("enabled", True)]
        self.wake_seconds = config.get("heartbeat.wake_seconds", 30)
        self.quiet_start = config.get("heartbeat.quiet_hours_start")
        self.quiet_end = config.get("heartbeat.quiet_hours_end")
        self.paused = False        # Tier 6 kill switch flips this
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- lifecycle ------------------------------------------------------------

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.wait(self.wake_seconds):
            if self.paused:
                continue
            try:
                self.tick()
            except Exception:
                self._log_error("heartbeat tick crashed")

    # -- one beat ---------------------------------------------------------------

    def tick(self, now: datetime | None = None) -> list[dict]:
        """Run whatever is due. Returns the notices created (tests use this)."""
        now = now or datetime.now()
        schedule = self._load_schedule()
        created = []
        for check in self.checks:
            name = check["name"]
            next_due = schedule.get(name)
            if next_due and now < datetime.fromisoformat(next_due):
                continue
            # one run per beat even if several intervals were missed — no pile-up
            schedule[name] = (now + timedelta(minutes=check.get("every_minutes", 60))).isoformat(sep=" ", timespec="seconds")
            self._save_schedule(schedule)
            created.extend(self._run_check(check, now))
        return created

    def _run_check(self, check: dict, now: datetime) -> list[dict]:
        fn = CHECK_TYPES.get(check.get("type"))
        if fn is None:
            self._log_error(f"unknown check type: {check.get('type')} (check '{check.get('name')}')")
            return []
        try:
            results = fn(check, self.config, now)
        except Exception:
            self._log_error(f"check '{check.get('name')}' failed")
            return []

        level = check.get("level", "notice")
        created = []
        for message, key in results:
            notice = self.board.add(message, level=level, key=key)
            if notice is None:
                continue   # deduped — already raised
            created.append(notice)
            self._maybe_push(notice, now)
        return created

    def _maybe_push(self, notice: dict, now: datetime) -> None:
        """Interrupt Tom only when it's warranted and allowed right now.
        Held notices surface later via the board's catch-up path."""
        if self.on_interrupt is None or notice["level"] == "notice":
            return
        if notice["level"] == "interrupt" and in_quiet_hours(now, self.quiet_start, self.quiet_end):
            return   # critical is the only level loud enough for quiet hours
        self.on_interrupt(notice)
        self.board.mark_seen([notice["id"]])

    # -- durable bits -----------------------------------------------------------

    def _load_schedule(self) -> dict:
        if self.schedule_path.exists():
            return json.loads(self.schedule_path.read_text())
        return {}

    def _save_schedule(self, schedule: dict) -> None:
        self.schedule_path.write_text(json.dumps(schedule, indent=2) + "\n")

    def _log_error(self, context: str) -> None:
        with open(ERROR_LOG, "a") as f:
            f.write(f"--- {datetime.now().isoformat()} {context}\n{traceback.format_exc()}\n")
