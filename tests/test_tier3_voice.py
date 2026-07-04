"""Tier 3: a spoken turn flows through the SAME brain as a typed turn,
speech starts at the first sentence, and a new press interrupts playback.
Real mic/speaker runs happen on the laptop; these fakes prove the wiring."""

import pytest

from trillion.brain import Brain
from trillion.config import Config
from trillion.provider import FakeProvider, Reply
from trillion.tools import build_default_registry
from trillion.voice import VoiceInterface
from trillion.voice.capture import pcm_to_wav
from trillion.voice.tts import SentenceBuffer


class FakeCapture:
    def __init__(self, recordings):
        self.recordings = list(recordings)
        self.on_press_calls = 0

    def record_once(self, on_press=None):
        if on_press:
            self.on_press_calls += 1
            on_press()
        return self.recordings.pop(0) if self.recordings else None


class FakeSTT:
    def __init__(self, transcripts):
        self.transcripts = list(transcripts)

    def transcribe(self, wav_bytes):
        assert wav_bytes  # audio actually arrived
        return self.transcripts.pop(0)


class FakeTTS:
    def __init__(self):
        self.buffer = SentenceBuffer()
        self.spoken = []
        self.stops = 0

    def feed(self, chunk):
        self.spoken.extend(self.buffer.feed(chunk))

    def flush(self):
        self.spoken.extend(self.buffer.flush())

    def stop(self):
        self.stops += 1


@pytest.fixture
def config():
    return Config()


def test_spoken_turn_uses_same_brain_and_tools(config, capsys):
    provider = FakeProvider(script=[
        Reply(content=[{"type": "tool_use", "id": "t1", "name": "get_dashboard",
                        "input": {"section": "whoop"}}], stop_reason="tool_use"),
        Reply(content=[{"type": "text", "text": "Recovery is 77% today. Solid."}]),
    ])
    brain = Brain(config, provider, registry=build_default_registry(config))
    tts = FakeTTS()
    voice = VoiceInterface(
        config, brain,
        capture=FakeCapture([pcm_to_wav(b"\x00\x00" * 800, 16000)]),
        stt=FakeSTT(["how's my recovery?"]),
        tts=tts,
    )

    transcript = voice.run_one_turn()

    assert transcript == "how's my recovery?"
    # the SAME brain: history holds the spoken turn and its tool exchange
    assert brain.history[0] == {"role": "user", "content": "how's my recovery?"}
    assert any(m["role"] == "user" and isinstance(m["content"], list) for m in brain.history)
    # the reply was spoken, sentence by sentence
    assert tts.spoken == ["Recovery is 77% today.", "Solid."]
    # the transcript is printed so ears-fault vs brain-fault is visible
    out = capsys.readouterr().out
    assert 'you (heard)> "how\'s my recovery?"' in out
    assert "thinking" in out


def test_new_press_interrupts_playback(config):
    brain = Brain(config, FakeProvider())
    tts = FakeTTS()
    capture = FakeCapture([pcm_to_wav(b"\x00\x00" * 800, 16000)])
    voice = VoiceInterface(config, brain, capture=capture, stt=FakeSTT(["hi"]), tts=tts)

    voice.run_one_turn()

    # pressing the key stopped any ongoing speech before recording started
    assert capture.on_press_calls == 1
    assert tts.stops == 1


def test_empty_transcript_is_skipped_not_sent(config):
    provider = FakeProvider()
    brain = Brain(config, provider)
    voice = VoiceInterface(
        config, brain,
        capture=FakeCapture([pcm_to_wav(b"\x00\x00" * 100, 16000)]),
        stt=FakeSTT(["   "]),
        tts=FakeTTS(),
    )
    assert voice.run_one_turn() is None
    assert provider.calls == []   # the brain was never bothered
    assert brain.history == []


def test_sentence_buffer_streams_sentences_early():
    buf = SentenceBuffer()
    out = buf.feed("Recovery is 77")
    assert out == []                          # incomplete sentence: hold
    out = buf.feed("% today. That's up from yes")
    assert out == ["Recovery is 77% today."]  # first sentence releases early
    out = buf.feed("terday!")
    assert out == []
    assert buf.flush() == ["That's up from yesterday!"]


def test_typed_repl_still_works_after_voice_exists(config):
    # Tier 3 must not fork or break the text path
    brain = Brain(config, FakeProvider())
    reply = brain.run_turn("still here?")
    assert "still here?" in reply
