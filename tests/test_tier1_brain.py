"""Tier 1: the brain holds a conversation, remembers within the session,
streams, and shrugs off provider failures without corrupting history."""

import pytest

from trillion.brain import Brain
from trillion.config import Config
from trillion.provider import FakeProvider, ProviderError


@pytest.fixture
def config():
    return Config()


def test_history_is_passed_back_each_turn(config):
    provider = FakeProvider()
    brain = Brain(config, provider)

    brain.run_turn("my name is Tom")
    brain.run_turn("I like morning meetings")
    reply = brain.run_turn("what did I say first?")

    # The fake echoes the first user message — only possible if the full
    # history reached the provider on turn 3.
    assert "my name is Tom" in reply
    assert "#3" in reply
    # And the provider really did receive all prior turns:
    last_call = provider.calls[-1]
    roles = [m["role"] for m in last_call["messages"]]
    assert roles == ["user", "assistant", "user", "assistant", "user"]


def test_system_prompt_carries_name_and_tone(config):
    provider = FakeProvider()
    brain = Brain(config, provider)
    brain.run_turn("hello")
    system = provider.calls[0]["system"]
    assert "Trillion" in system
    assert "warm" in system


def test_streaming_callback_receives_text(config):
    provider = FakeProvider()
    brain = Brain(config, provider)
    chunks = []
    reply = brain.run_turn("stream me", on_text=chunks.append)
    assert "".join(chunks) == reply != ""


def test_provider_failure_rolls_back_history(config):
    class DownProvider(FakeProvider):
        def complete(self, *a, **kw):
            raise ProviderError("Couldn't reach the model.")

    brain = Brain(config, DownProvider())
    with pytest.raises(ProviderError):
        brain.run_turn("hello?")
    assert brain.history == []  # no half-finished exchange left behind

    # And the brain still works afterwards with a healthy provider:
    brain.provider = FakeProvider()
    assert brain.run_turn("are you back?")
