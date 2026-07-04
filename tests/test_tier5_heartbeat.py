"""Tier 5: checks fire once when due, notices are held for Tom's return,
restarts resume the schedule, quiet hours hold interruptions, dismiss clears."""

import json
from datetime import datetime, timedelta

import pytest

from trillion.config import Config
from trillion.heartbeat import Heartbeat, in_quiet_hours
from trillion.notices import NoticeBoard
from trillion.tools import focus as focus_mod

NOW = datetime(2026, 7, 4, 10, 0, 0)   # a Saturday morning, outside quiet hours


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def board(tmp_path):
    return NoticeBoard(path=tmp_path / "notices.json")


def make_heartbeat(config, board, tmp_path, checks, on_interrupt=None):
    hb = Heartbeat(config, board, schedule_path=tmp_path / "schedule.json",
                   on_interrupt=on_interrupt)
    hb.checks = checks
    return hb


def trigger_check(tmp_path, **overrides):
    """A file_exists check pointed at a file we control."""
    trigger = tmp_path / "trigger.txt"
    check = {"name": "demo", "type": "file_exists", "path": str(trigger),
             "every_minutes": 5, "level": "interrupt"}
    check.update(overrides)
    return check, trigger


def test_check_fires_once_and_dedupes(config, board, tmp_path, monkeypatch):
    monkeypatch.setattr("trillion.heartbeat.ROOT", tmp_path.parent)  # keep paths absolute-safe
    check, trigger = trigger_check(tmp_path)
    hb = make_heartbeat(config, board, tmp_path, [check])

    assert hb.tick(NOW) == []                       # condition not met: silence
    trigger.write_text("go")
    created = hb.tick(NOW + timedelta(minutes=6))   # due again, condition met
    assert len(created) == 1
    # due again, same trigger file → deduped by key, not raised twice
    assert hb.tick(NOW + timedelta(minutes=12)) == []
    assert len(board.pending()) == 1


def test_not_due_means_not_run(config, board, tmp_path):
    check, trigger = trigger_check(tmp_path)
    trigger.write_text("go")
    hb = make_heartbeat(config, board, tmp_path, [check])
    assert len(hb.tick(NOW)) == 1
    assert hb.tick(NOW + timedelta(minutes=1)) == []   # 5-minute check: too soon


def test_notice_is_held_for_toms_return(config, board, tmp_path):
    # heartbeat notices something while no interface is open (on_interrupt=None)
    check, trigger = trigger_check(tmp_path)
    trigger.write_text("go")
    make_heartbeat(config, board, tmp_path, [check]).tick(NOW)

    # Tom comes back: the notice is waiting, unseen
    unseen = board.unseen()
    assert len(unseen) == 1 and "Trigger file noticed" in unseen[0]["message"]
    board.mark_seen([unseen[0]["id"]])
    assert board.unseen() == []                     # shown once…
    assert len(board.pending()) == 1                # …but pending until dismissed
    assert board.dismiss(unseen[0]["id"])
    assert board.pending() == []                    # dismissed: cleared


def test_restart_resumes_schedule_instead_of_refiring(config, board, tmp_path):
    check, trigger = trigger_check(tmp_path)
    trigger.write_text("go")
    hb1 = make_heartbeat(config, board, tmp_path, [check])
    hb1.tick(NOW)

    # "restart": a new Heartbeat over the same schedule file, 1 minute later
    hb2 = make_heartbeat(config, board, tmp_path, [check])
    assert hb2.tick(NOW + timedelta(minutes=1)) == []   # timer survived the restart
    schedule = json.loads((tmp_path / "schedule.json").read_text())
    assert "demo" in schedule


def test_quiet_hours_hold_interrupts_but_not_critical(config, tmp_path):
    pushed = []
    board = NoticeBoard(path=tmp_path / "notices.json")
    check, trigger = trigger_check(tmp_path)
    trigger.write_text("go")
    hb = make_heartbeat(config, board, tmp_path, [check], on_interrupt=pushed.append)
    hb.quiet_start, hb.quiet_end = "22:30", "07:00"

    night = datetime(2026, 7, 4, 23, 30)
    hb.tick(night)
    assert pushed == []                       # held — not lost:
    assert len(board.unseen()) == 1           # waiting in the catch-up set

    # critical ignores quiet hours
    trigger.write_text("again")               # new mtime → new dedupe key
    check2, _ = trigger_check(tmp_path, name="critical_demo", level="critical")
    hb.checks = [check2]
    import os, time
    os.utime(trigger, (time.time() + 9, time.time() + 9))   # force distinct mtime/key
    hb.tick(night + timedelta(minutes=6))
    assert len(pushed) == 1


def test_reminder_due_check_delivers_and_marks_done(config, board, tmp_path, monkeypatch):
    monkeypatch.setattr(focus_mod, "REMINDERS_PATH", tmp_path / "reminders.json")
    focus_mod.add_reminder("Submit NHBC inspection request", "2026-07-04 09:00")

    check = {"name": "reminders", "type": "reminder_due", "every_minutes": 1, "level": "interrupt"}
    hb = make_heartbeat(config, board, tmp_path, [check])
    created = hb.tick(NOW)   # 10:00 — reminder was due at 09:00

    assert len(created) == 1 and "NHBC" in created[0]["message"]
    assert all(r["done"] for r in focus_mod._load_reminders())
    assert hb.tick(NOW + timedelta(minutes=2)) == []   # delivered once, stays on the board


def test_failing_check_never_kills_the_beat(config, board, tmp_path):
    bad = {"name": "bad", "type": "no_such_type", "every_minutes": 1, "level": "notice"}
    good, trigger = trigger_check(tmp_path, name="good")
    trigger.write_text("go")
    hb = make_heartbeat(config, board, tmp_path, [bad, good])
    created = hb.tick(NOW)   # must not raise; the good check still runs
    assert len(created) == 1


def test_quiet_hours_math():
    assert in_quiet_hours(datetime(2026, 7, 4, 23, 0), "22:30", "07:00")
    assert in_quiet_hours(datetime(2026, 7, 4, 6, 59), "22:30", "07:00")
    assert not in_quiet_hours(datetime(2026, 7, 4, 12, 0), "22:30", "07:00")
    assert not in_quiet_hours(datetime(2026, 7, 4, 12, 0), None, None)
