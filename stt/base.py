"""Speech-to-text pipeline using OpenAI APIs with fallbacks."""
from __future__ import annotations

import os
import select
import sys
import time
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
            raw = self._timed_input(timeout)
            if raw is None:
                return TranscriptionResult(text="", timed_out=True)
        else:
            raw = None
        try:
            if raw is None:
                raw = input("Speak now (type your request): ")
        except (EOFError, KeyboardInterrupt):
            raw = ""
        return TranscriptionResult(text=clean_transcription(raw), timed_out=False)

    def _timed_input(self, timeout: float) -> Optional[str]:
        """Return input text if available before timeout; otherwise None."""
        if os.name == "nt":
            return self._timed_input_windows(timeout)

        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return None
        return input("Speak now (type your request): ")

    def _timed_input_windows(self, timeout: float) -> Optional[str]:
        """Windows-compatible timed input using msvcrt."""
        try:
            import msvcrt
        except ImportError:  # pragma: no cover - platform guard
            return None

        prompt = "Speak now (type your request): "
        print(prompt, end="", flush=True)
        buffer: list[str] = []
        start = time.time()

        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    print()
                    return "".join(buffer)
                if ch == "\003":  # Ctrl+C
                    raise KeyboardInterrupt
                if ch in ("\b", "\x7f"):
                    if buffer:
                        buffer.pop()
                        print("\b \b", end="", flush=True)
                else:
                    buffer.append(ch)
                    print(ch, end="", flush=True)

            if time.time() - start >= timeout:
                if buffer:
                    print()
                    return "".join(buffer)
                print()
                return None

            time.sleep(0.05)


__all__ = ["SpeechToTextEngine", "TranscriptionResult"]
