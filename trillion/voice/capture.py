"""Push-to-talk microphone capture: record while the key is held, stop on
release. No open mic, no voice-activity guessing — and because we only ever
record while the key is down, Trillion can't hear itself speak.

Needs sounddevice + pynput (see requirements.txt); imported lazily so text
mode never touches audio.
"""

from __future__ import annotations

import io
import threading
import wave


class PushToTalkCapture:
    def __init__(self, config):
        import sounddevice  # noqa: F401 — fail here, loudly, if audio is unavailable
        from pynput import keyboard

        self._sd = sounddevice
        self._keyboard = keyboard
        self.sample_rate = config.get("voice.sample_rate", 16000)
        key_name = config.get("voice.ptt_key", "space")
        self.key = getattr(keyboard.Key, key_name, None) or keyboard.KeyCode.from_char(key_name)

    def record_once(self, on_press=None) -> bytes | None:
        """Block until one full press→release cycle; return WAV bytes.
        on_press fires the moment the key goes down (used to cut off TTS)."""
        pressed = threading.Event()
        released = threading.Event()

        def handle_press(key):
            if key == self.key and not pressed.is_set():
                pressed.set()
                if on_press:
                    on_press()

        def handle_release(key):
            if key == self.key and pressed.is_set():
                released.set()
                return False  # stop the listener

        frames: list[bytes] = []

        def audio_callback(indata, frame_count, time_info, status):
            frames.append(bytes(indata))

        listener = self._keyboard.Listener(on_press=handle_press, on_release=handle_release)
        listener.start()
        try:
            # wait in short slices so Ctrl+C still works
            while not pressed.wait(timeout=0.1):
                pass
            with self._sd.RawInputStream(
                samplerate=self.sample_rate, channels=1, dtype="int16",
                callback=audio_callback,
            ):
                while not released.wait(timeout=0.05):
                    pass
        finally:
            listener.stop()

        if not frames:
            return None
        return pcm_to_wav(b"".join(frames), self.sample_rate)


def pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)   # int16
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()
