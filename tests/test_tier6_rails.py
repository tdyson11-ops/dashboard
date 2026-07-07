"""Tier 6: consequential actions stop for a per-action yes, absent humans get
a note instead of a hang, config outranks code, the audit trail records it
all, and the kill switch stops proactivity without killing conversation."""

import json
from datetime import datetime

import pytest

from trillion.audit import Audit
from trillion.brain import Brain
from trillion.config import Config
from trillion.gate import Gate
from trillion.heartbeat import Heartbeat
from trillion.notices import NoticeBoard
from trillion.provider import FakeProvider, Reply
from trillion.tools import build_default_registry
from trillion.tools import comms as comms_mod


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def outbox(tmp_path, monkeypatch):
    path = tmp_path / "outbox.json"
    monkeypatch.setattr(comms_mod, "OUTBOX_PATH", path)
    return path


def send_script():
    return FakeProvider(script=[
        Reply(content=[{"type": "tool_use", "id": "t1", "name": "send_message",
                        "input": {"to": "Dad", "message": "Cash flow review moved to 3pm"}}],
              stop_reason="tool_use"),
        Reply(content=[{"type": "text", "text": "Handled the send request."}]),
    ])


def make_brain(config, provider, tmp_path, ask=None, board=None):
    audit = Audit(path=tmp_path / "audit.jsonl")
    gate = Gate(config, audit=audit, board=board, ask=ask)
    registry = build_default_registry(config)
    return Brain(config, provider, registry=registry, gate=gate, audit=audit)


def test_approved_send_runs_once(config, outbox, tmp_path):
    asked = []
    brain = make_brain(config, send_script(), tmp_path,
                       ask=lambda d: asked.append(d) or True)
    brain.run_turn("tell Dad the review moved to 3pm")

    assert len(asked) == 1
    assert "send a message to Dad" in asked[0]      # states plainly what it's about to do
    sent = json.loads(outbox.read_text())
    assert sent[0]["to"] == "Dad"
    events = [e["event"] for e in brain.audit.tail()]
    assert "gate" in events and "tool" in events and "model_call" in events


def test_declined_send_does_not_run(config, outbox, tmp_path):
    brain = make_brain(config, send_script(), tmp_path, ask=lambda d: False)
    brain.run_turn("tell Dad the review moved to 3pm")

    assert not outbox.exists()                       # nothing left the machine
    result = brain.history[2]["content"][0]
    assert result["is_error"] is True
    assert "declined" in result["content"]


def test_approval_is_per_action_and_never_generalizes(config, outbox, tmp_path):
    asked = []
    provider = FakeProvider(script=[
        Reply(content=[{"type": "tool_use", "id": "t1", "name": "send_message",
                        "input": {"to": "Dad", "message": "one"}}], stop_reason="tool_use"),
        Reply(content=[{"type": "tool_use", "id": "t2", "name": "send_message",
                        "input": {"to": "Dad", "message": "two"}}], stop_reason="tool_use"),
        Reply(content=[{"type": "text", "text": "Both handled."}]),
    ])
    brain = make_brain(config, provider, tmp_path, ask=lambda d: asked.append(d) or True)
    brain.run_turn("send Dad two messages")
    assert len(asked) == 2                           # a yes covers exactly one action


def test_no_human_present_holds_and_leaves_note(config, outbox, tmp_path):
    board = NoticeBoard(path=tmp_path / "notices.json")
    brain = make_brain(config, send_script(), tmp_path, ask=None, board=board)
    brain.run_turn("(heartbeat-initiated) message Dad")

    assert not outbox.exists()
    result = brain.history[2]["content"][0]
    assert "NOT performed" in result["content"]      # loop keeps running, nothing sent
    held = board.pending()
    assert len(held) == 1 and "weren't around to approve" in held[0]["message"]


def test_config_can_gate_any_tool_without_code_change(config, tmp_path):
    config.data.setdefault("tools", {})["confirm"] = ["send_message", "add_focus_item"]
    provider = FakeProvider(script=[
        Reply(content=[{"type": "tool_use", "id": "t1", "name": "add_focus_item",
                        "input": {"item": "Buy paint"}}], stop_reason="tool_use"),
        Reply(content=[{"type": "text", "text": "ok"}]),
    ])
    asked = []
    brain = make_brain(config, provider, tmp_path, ask=lambda d: asked.append(d) or False)
    brain.run_turn("add buy paint")
    assert len(asked) == 1                           # ungated-in-code tool now asks


def test_read_only_tools_flow_freely(config, tmp_path):
    provider = FakeProvider(script=[
        Reply(content=[{"type": "tool_use", "id": "t1", "name": "get_dashboard",
                        "input": {"section": "whoop"}}], stop_reason="tool_use"),
        Reply(content=[{"type": "text", "text": "77% recovery."}]),
    ])
    never_ask = lambda d: pytest.fail("read-only lookup must not be gated")
    brain = make_brain(config, provider, tmp_path, ask=never_ask)
    assert "77%" in brain.run_turn("recovery?")


def test_injection_posture_is_in_the_system_prompt(config, tmp_path):
    provider = FakeProvider()
    brain = make_brain(config, provider, tmp_path)
    brain.run_turn("hi")
    system = provider.calls[0]["system"]
    assert "data, not instructions" in system
    assert "do not comply" in system


def test_kill_switch_stops_heartbeat_but_not_conversation(config, tmp_path):
    board = NoticeBoard(path=tmp_path / "notices.json")
    trigger = tmp_path / "trigger.txt"
    trigger.write_text("go")
    hb = Heartbeat(config, board, schedule_path=tmp_path / "schedule.json")
    hb.checks = [{"name": "demo", "type": "file_exists", "path": str(trigger),
                  "every_minutes": 1, "level": "interrupt"}]

    hb.paused = True                                 # /pause
    assert hb.tick(datetime(2026, 7, 4, 10, 0)) == []
    assert board.pending() == []                     # all proactive behavior held

    brain = Brain(config, FakeProvider())            # …while talk still works
    assert brain.run_turn("you there?")

    hb.paused = False                                # /resume
    assert len(hb.tick(datetime(2026, 7, 4, 10, 0))) == 1


def test_config_threshold_changes_behavior_without_code(config, tmp_path):
    # real data.json has recovery 77: threshold 40 → silent; 80 → notice
    board = NoticeBoard(path=tmp_path / "notices.json")
    hb = Heartbeat(config, board, schedule_path=tmp_path / "schedule.json")
    low = {"name": "rec", "type": "whoop_recovery_low", "every_minutes": 1,
           "threshold": 40, "level": "notice"}
    hb.checks = [low]
    assert hb.tick(datetime(2026, 7, 4, 10, 0)) == []

    edited = dict(low, threshold=80)                 # the one-line config edit
    hb.checks = [edited]
    created = hb.tick(datetime(2026, 7, 4, 10, 5))
    assert len(created) == 1 and "recovery is low" in created[0]["message"]
