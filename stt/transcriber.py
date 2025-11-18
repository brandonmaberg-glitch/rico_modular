"""Speech-to-text pipeline using OpenAI or a fallback text input."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:  # Optional dependency for Whisper/Realtime usage
    from openai import OpenAI
except Exception:  # pragma: no cover - library import guard
    OpenAI = None  # type: ignore


def clean_transcript(text: str) -> str:
    """Return lowercase transcription without punctuation."""

    filtered = ''.join(ch for ch in text if ch.isalnum() or ch.isspace())
    return ' '.join(filtered.split()).lower()


@dataclass
class SpeechToText:
    """Handle speech recognition with a graceful fallback."""

    api_key: Optional[str]

    def __post_init__(self) -> None:
        self._client = None
        if self.api_key and OpenAI:
            try:
                self._client = OpenAI(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[RICO] Failed to initialize OpenAI client: {exc}")
                self._client = None

    def capture_and_transcribe(self) -> Optional[str]:
        """Capture audio from microphone or console and return clean text."""

        if not self._client:
            return self._fallback_transcription()

        # Placeholder: real implementation would stream microphone audio.
        print("[RICO] OpenAI STT placeholder engaged. Type what you said:")
        return self._fallback_transcription()

    def _fallback_transcription(self) -> Optional[str]:
        """Use synchronous console input to mimic transcription."""

        try:
            raw_text = input("Dictate your request (blank to cancel): ")
        except EOFError:
            return None

        cleaned = clean_transcript(raw_text)
        return cleaned or None
