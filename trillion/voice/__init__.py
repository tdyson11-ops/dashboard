"""The ears and mouth. This wraps the SAME brain the text REPL uses — voice
only changes how a turn arrives (mic → Deepgram) and leaves (ElevenLabs →
speaker). If you find yourself duplicating agent logic here, stop.

capture / stt / tts are injectable so the whole pipeline runs offline in
tests with fakes; the real classes import sounddevice/pynput lazily.
"""

from __future__ import annotations

from ..provider import ProviderError


class VoiceInterface:
    def __init__(self, config, brain, capture, stt, tts):
        self.config = config
        self.brain = brain
        self.capture = capture
        self.stt = stt
        self.tts = tts

    def run_one_turn(self) -> str | None:
        """One spoken exchange: record → transcribe → think → speak.
        Returns the transcript (None if nothing usable was heard)."""
        # Pressing the key while Trillion is talking cuts it off — on_press
        # stops playback the instant recording starts.
        audio = self.capture.record_once(on_press=self.tts.stop)
        if audio is None:
            return None

        print("(heard you — thinking…)", flush=True)   # silence must never read as "it broke"
        transcript = self.stt.transcribe(audio)
        print(f'you (heard)> "{transcript}"')           # so Tom can tell ears-fault from brain-fault
        if not transcript.strip():
            print("(heard nothing usable — hold the key and speak)")
            return None

        name = self.config.get("assistant.name", "Trillion")
        print(f"{name}> ", end="", flush=True)
        try:
            self.brain.run_turn(transcript, on_text=self._on_text)
            self.tts.flush()   # speak whatever's left in the sentence buffer
            print()
        except ProviderError as e:
            print(f"\n[{e}]")
        return transcript

    def _on_text(self, chunk: str) -> None:
        print(chunk, end="", flush=True)   # text stays visible alongside speech
        self.tts.feed(chunk)               # speech starts at the first full sentence

    def run(self) -> None:
        name = self.config.get("assistant.name", "Trillion")
        key = self.config.get("voice.ptt_key", "space")
        print(f"{name} — voice mode. Hold [{key}] to talk, release to send. Ctrl+C to exit.\n")
        try:
            while True:
                self.run_one_turn()
        except KeyboardInterrupt:
            print("\n(voice mode ended)")
        finally:
            self.tts.stop()


def build_voice_interface(config, brain) -> VoiceInterface:
    """Real capture + Deepgram + ElevenLabs. Raises RuntimeError with a
    human explanation if a dependency or key is missing."""
    from .capture import PushToTalkCapture
    from .stt import DeepgramSTT
    from .tts import ElevenLabsTTS

    missing = [k for k in ("DEEPGRAM_API_KEY", "ELEVENLABS_API_KEY") if not config.secret(k)]
    if missing:
        raise RuntimeError(
            f"Voice mode needs {' and '.join(missing)} in .env (see .env.example)."
        )
    return VoiceInterface(
        config,
        brain,
        capture=PushToTalkCapture(config),
        stt=DeepgramSTT(config),
        tts=ElevenLabsTTS(config),
    )
