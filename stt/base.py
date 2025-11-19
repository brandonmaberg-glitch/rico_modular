"""Speech-to-text pipeline using OpenAI APIs with fallbacks."""
from __future__ import annotations

import select
import sys
from dataclasses import dataclass
from typing import Optional

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

from utils.text import clean_transcription


@dataclass
class TranscriptionResult:
    """Container for speech-to-text results."""

    text: str
    timed_out: bool = False


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

    def transcribe(self, timeout: Optional[float] = None) -> TranscriptionResult:
        """Return a cleaned transcription of the current user request."""
        if not self._client:
            return self._fallback_transcription(timeout)

        # Placeholder: replace with real audio capture + Whisper call.
        # To keep the runtime interactive without audio, fall back to text input.
        return self._fallback_transcription(timeout)

    def _fallback_transcription(self, timeout: Optional[float]) -> TranscriptionResult:
        """Text-based fallback that simulates transcription with an optional timeout."""
        if timeout is not None:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if not ready:
                return TranscriptionResult(text="", timed_out=True)
        try:
            if raw is None:
                raw = input("Speak now (type your request): ")
        except (EOFError, KeyboardInterrupt):
            raw = ""
        return TranscriptionResult(text=clean_transcription(raw), timed_out=False)


__all__ = ["SpeechToTextEngine", "TranscriptionResult"]
