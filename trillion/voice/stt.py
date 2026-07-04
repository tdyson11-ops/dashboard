"""The ears' seam: give me audio, get back text. Deepgram today; swapping
transcribers means editing only this file."""

from __future__ import annotations

import requests


class DeepgramSTT:
    def __init__(self, config):
        self.api_key = config.secret("DEEPGRAM_API_KEY")
        self.model = config.get("voice.stt_model", "nova-3")

    def transcribe(self, wav_bytes: bytes) -> str:
        response = requests.post(
            "https://api.deepgram.com/v1/listen",
            params={"model": self.model, "smart_format": "true"},
            headers={
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/wav",
            },
            data=wav_bytes,
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        try:
            return body["results"]["channels"][0]["alternatives"][0]["transcript"]
        except (KeyError, IndexError):
            return ""
