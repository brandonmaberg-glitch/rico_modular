"""Speech-to-text pipeline using OpenAI APIs with fallbacks."""
from __future__ import annotations

from typing import Optional

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

from utils.text import clean_transcription


class SpeechToTextEngine:
    """Wrapper around OpenAI Whisper with a graceful fallback."""

    def __init__(self, api_key: Optional[str]) -> None:
        self.api_key = api_key
        self._client = None
        if api_key and OpenAI:
            try:
                self._client = OpenAI(api_key=api_key)
            except Exception:
                self._client = None

    def transcribe(self) -> str:
        """Return a cleaned transcription of the current user request."""
        if not self._client:
            return self._fallback_transcription()

        # Placeholder: replace with real audio capture + Whisper call.
        # To keep the runtime interactive without audio, fall back to text input.
        return self._fallback_transcription()

    def _fallback_transcription(self) -> str:
        """Text-based fallback that simulates transcription."""
        try:
            raw = input("Speak now (type your request): ")
        except (EOFError, KeyboardInterrupt):
            raw = ""
        return clean_transcription(raw)


__all__ = ["SpeechToTextEngine"]
