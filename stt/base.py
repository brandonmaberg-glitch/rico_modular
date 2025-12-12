"""Speech-to-text pipeline using OpenAI APIs with fallbacks."""
from __future__ import annotations

import logging
import os
import select
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

from rico.voice.ptt_input import record_to_wav
from rico.voice.transcribe import transcribe_wav
from utils.text import clean_transcription


logger = logging.getLogger("RICO")


@dataclass
class TranscriptionResult:
    """Container for speech-to-text results."""

    text: str
    timed_out: bool = False


class SpeechToTextEngine:
    """Wrapper around OpenAI Whisper with a graceful fallback."""

    def __init__(
        self,
        api_key: Optional[str],
        *,
        voice_enabled: bool = False,
        voice_key: str = "v",
        voice_sample_rate: int = 16000,
        voice_max_seconds: int = 20,
    ) -> None:
        self.api_key = api_key
        self._client = None
        self.voice_enabled = voice_enabled
        self.voice_key = (voice_key or "v").lower()
        self.voice_sample_rate = voice_sample_rate
        self.voice_max_seconds = voice_max_seconds
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
        try:
            raw, timed_out = self._read_text_input(timeout)
        except (EOFError, KeyboardInterrupt):
            raw, timed_out = "", False

        if timed_out:
            return TranscriptionResult(text="", timed_out=True)

        voice_text = self._maybe_handle_voice_shortcut(raw, timeout)
        if voice_text is not None:
            return TranscriptionResult(text=clean_transcription(voice_text), timed_out=False)

        return TranscriptionResult(text=clean_transcription(raw), timed_out=False)

    def _maybe_handle_voice_shortcut(self, raw: str, timeout: Optional[float]) -> Optional[str]:
        """Handle push-to-talk trigger and return transcribed text when available."""

        if raw.strip().lower() != self.voice_key:
            return None

        if not self.voice_enabled:
            print("Voice is disabled. Set VOICE_ENABLED=true to use push-to-talk.")
            return self._retry_text_input(timeout)

        output_path = record_to_wav(
            sample_rate=self.voice_sample_rate,
            max_seconds=self.voice_max_seconds,
        )
        if not output_path:
            print("Falling back to typed input.")
            return self._retry_text_input(timeout)

        transcript = transcribe_wav(output_path)
        if not transcript:
            print("Falling back to typed input.")
            return self._retry_text_input(timeout)
        return transcript

    def _retry_text_input(self, timeout: Optional[float]) -> Optional[str]:
        try:
            raw, timed_out = self._read_text_input(timeout)
        except (EOFError, KeyboardInterrupt):
            return ""

        if timed_out:
            return ""

        return raw

    def _read_text_input(self, timeout: Optional[float]) -> Tuple[str, bool]:
        """Read text from stdin with an optional timeout, supporting Windows consoles."""

        if os.name == "nt":
            return self._read_text_input_windows(timeout)
        return self._read_text_input_posix(timeout)

    def _read_text_input_posix(self, timeout: Optional[float]) -> Tuple[str, bool]:
        """Read text input on POSIX systems using select for optional timeout."""

        if timeout is not None:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if not ready:
                return "", True

        raw = input("Speak now (type your request): ")
        return raw, False

    def _read_text_input_windows(self, timeout: Optional[float]) -> Tuple[str, bool]:
        """Read text input on Windows consoles without relying on select.select."""

        import msvcrt  # noqa: WPS433 - Windows-specific import

        prompt = "Speak now (type your request): "
        sys.stdout.write(prompt)
        sys.stdout.flush()

        buffer: list[str] = []
        end_time = time.monotonic() + timeout if timeout is not None else None

        while True:
            if end_time is not None and time.monotonic() >= end_time and not msvcrt.kbhit():
                sys.stdout.write("\n")
                sys.stdout.flush()
                return "", True

            if not msvcrt.kbhit():
                time.sleep(0.01)
                continue

            char = msvcrt.getwch()

            if char in ("\r", "\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                return "".join(buffer), False
            if char == "\003":  # Ctrl+C
                raise KeyboardInterrupt
            if char in ("\b", "\x7f"):
                if buffer:
                    buffer.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue

            buffer.append(char)
            sys.stdout.write(char)
            sys.stdout.flush()


__all__ = ["SpeechToTextEngine", "TranscriptionResult"]
