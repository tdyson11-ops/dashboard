"""Tier 2: the model calls tools through the registry, results flow back into
the conversation, and failures become plain-language errors — never crashes."""

import json

import pytest

from trillion.brain import Brain
from trillion.config import Config
from trillion.provider import FakeProvider, Reply
from trillion.tools import build_default_registry
from trillion.tools import focus as focus_mod


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def registry(config, tmp_path, monkeypatch):
    # keep tests off the real data.json / reminders.json
    data = tmp_path / "data.json"
    data.write_text(json.dumps({"updated": "today", "focus": ["Call the site manager"]}))
    monkeypatch.setattr(focus_mod, "DATA_PATH", data)
    monkeypatch.setattr(focus_mod, "REMINDERS_PATH", tmp_path / "reminders.json")
    return build_default_registry(config)


def tool_call(name, args, call_id="tc_1"):
    return {"type": "tool_use", "id": call_id, "name": name, "input": args}


def test_model_calls_tool_and_uses_result(config, registry):
    provider = FakeProvider(script=[
        Reply(content=[tool_call("get_focus_list", {})], stop_reason="tool_use"),
        Reply(content=[{"type": "text", "text": "One thing today: call the site manager."}]),
    ])
    brain = Brain(config, provider, registry=registry)

    reply = brain.run_turn("what's on my list for today?")

    assert "site manager" in reply
    # The second provider call must have received the tool result:
    second_call_messages = provider.calls[1]["messages"]
    result_msg = second_call_messages[-1]
    assert result_msg["role"] == "user"
    assert result_msg["content"][0]["type"] == "tool_result"
    assert "Call the site manager" in result_msg["content"][0]["content"]
    # And the provider was offered the tool schemas:
    assert any(t["name"] == "get_focus_list" for t in provider.calls[0]["tools"])


def test_multiple_tool_calls_in_sequence(config, registry):
    provider = FakeProvider(script=[
        Reply(content=[tool_call("get_focus_list", {}, "tc_1")], stop_reason="tool_use"),
        Reply(content=[tool_call("add_focus_item", {"item": "Buy paint"}, "tc_2")], stop_reason="tool_use"),
        Reply(content=[{"type": "text", "text": "Done — added paint to the list."}]),
    ])
    brain = Brain(config, provider, registry=registry)
    reply = brain.run_turn("add buy paint to my list")
    assert "added paint" in reply.lower()
    assert "Buy paint" in registry.run("get_focus_list", {})[0]


def test_failing_tool_returns_error_to_model_not_crash(config, registry, monkeypatch):
    # break the tool on purpose: point it at a missing file
    monkeypatch.setattr(focus_mod, "DATA_PATH", focus_mod.DATA_PATH.parent / "gone.json")
    provider = FakeProvider(script=[
        Reply(content=[tool_call("get_focus_list", {})], stop_reason="tool_use"),
        Reply(content=[{"type": "text", "text": "I couldn't read your list just now."}]),
    ])
    brain = Brain(config, provider, registry=registry)

    reply = brain.run_turn("what's on my list?")   # must not raise

    assert "couldn't read" in reply
    result = provider.calls[1]["messages"][-1]["content"][0]
    assert result.get("is_error") is True
    assert "failed" in result["content"]


def test_unknown_tool_and_missing_args_are_plain_language(registry):
    out, err = registry.run("no_such_tool", {})
    assert err and "no tool called" in out.lower()
    out, err = registry.run("add_focus_item", {})
    assert err and "missing input" in out


def test_reminders_roundtrip(registry):
    out, err = registry.run("add_reminder", {"text": "Submit NHBC form", "due": "2026-07-10 09:00"})
    assert not err and "Reminder #1" in out
    out, err = registry.run("list_reminders", {})
    assert not err and "Submit NHBC form" in out


def test_dashboard_reads_real_sections(config):
    # against the repo's real data.json — read-only
    registry = build_default_registry(config)
    out, err = registry.run("get_dashboard", {"section": "university"})
    assert not err and "Construction Management" in out
    out, err = registry.run("get_dashboard", {"section": "whoop"})
    assert not err and "recovery" in out
