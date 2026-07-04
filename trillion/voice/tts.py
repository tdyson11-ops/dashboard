"""The mouth's seam: feed me text, I speak it aloud. ElevenLabs today.

Streaming shape: feed() receives text chunks as the brain streams them and
enqueues each completed sentence; a worker thread synthesizes and plays
sentence by sentence, so Trillion starts talking while the reply is still
being written. stop() cuts everything off instantly (interruption).
"""

from __future__ import annotations

import queue
import re
import threading

import requests

# A sentence is only "done" once whitespace follows its end punctuation —
# end-of-chunk is not a boundary (the next chunk may continue "2.5", "Dr.", …);
# whatever remains is released by flush() when the reply is complete.
_SENTENCE_END = re.compile(r'(.*?[.!?]["\')\]]*)\s+', re.S)

PCM_RATE = 22050  # matches output_format=pcm_22050


class SentenceBuffer:
    """Accumulates streamed text chunks and yields complete sentences, so
    speech can begin before the whole reply is written."""

    def __init__(self):
        self._buffer = ""

    def feed(self, chunk: str) -> list[str]:
        self._buffer += chunk
        sentences = []
        while True:
            match = _SENTENCE_END.match(self._buffer)
            if not match or match.end() == 0:
                break
            sentence = match.group(1).strip()
            self._buffer = self._buffer[match.end():]
            if len(sentence) > 1:
                sentences.append(sentence)
        return sentences

    def flush(self) -> list[str]:
        leftover = self._buffer.strip()
        self._buffer = ""
        return [leftover] if len(leftover) > 1 else []


class ElevenLabsTTS:
    def __init__(self, config):
        import sounddevice

        self._sd = sounddevice
        self.api_key = config.secret("ELEVENLABS_API_KEY")
        self.voice_id = config.get("voice.voice_id", "21m00Tcm4TlvDq8ikWAM")
        self.model = config.get("voice.tts_model", "eleven_flash_v2_5")
        self._sentences = SentenceBuffer()
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._run_worker, daemon=True)
        self._worker.start()

    # -- feeding text ---------------------------------------------------------

    def feed(self, chunk: str) -> None:
        self._stop.clear()
        for sentence in self._sentences.feed(chunk):
            self._queue.put(sentence)

    def flush(self) -> None:
        for sentence in self._sentences.flush():
            self._queue.put(sentence)

    def speak(self, text: str) -> None:
        self.feed(text)
        self.flush()

    def stop(self) -> None:
        """Interrupt: drop queued sentences and halt playback now."""
        self._stop.set()
        self._sentences = SentenceBuffer()
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

    # -- worker ---------------------------------------------------------------

    def _run_worker(self) -> None:
        while True:
            sentence = self._queue.get()
            if sentence is None:
                return
            if self._stop.is_set():
                continue
            try:
                self._play_sentence(sentence)
            except Exception as e:
                # speech failing must not kill the app — the text is on screen
                print(f"\n[voice: playback failed: {e}]", flush=True)

    def _play_sentence(self, sentence: str) -> None:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream",
            params={"output_format": f"pcm_{PCM_RATE}"},
            headers={"xi-api-key": self.api_key},
            json={"text": sentence, "model_id": self.model},
            stream=True,
            timeout=30,
        )
        response.raise_for_status()
        with self._sd.RawOutputStream(samplerate=PCM_RATE, channels=1, dtype="int16") as out:
            for chunk in response.iter_content(chunk_size=4096):
                if self._stop.is_set():
                    break
                if chunk:
                    out.write(chunk)
