"""Text-to-speech utilities using ElevenLabs with safe fallbacks."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import uuid

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import save as el_save
except Exception:  # pragma: no cover - optional dependency guard
    ElevenLabs = None  # type: ignore
    el_save = None  # type: ignore


def _default_audio_path() -> Path:
    return Path("logs") / f"rico_tts_{uuid.uuid4().hex}.mp3"


@dataclass
class TextToSpeech:
    """Convert responses to speech using ElevenLabs when available."""

    api_key: Optional[str]
    voice_id: Optional[str]

    def __post_init__(self) -> None:
        self._client = None
        if self.api_key and ElevenLabs:
            try:
                self._client = ElevenLabs(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"[RICO] Failed to initialize ElevenLabs client: {exc}")
                self._client = None

    def speak(self, text: str) -> None:
        """Synthesize speech and play or log a fallback message."""

        if not text:
            return

        if not self._client:
            print(f"[RICO:VOICE] {text}")
            return

        try:
            audio = self._client.generate(text=text, voice=self.voice_id or "Rachel")
            output_path = _default_audio_path()
            if el_save:
                el_save(audio, output_path)
                print(f"[RICO] Audio saved to {output_path.resolve()}")
            else:  # pragma: no cover - defensive
                print("[RICO] Audio generated but playback helper missing.")
        except Exception as exc:
            print(f"[RICO] ElevenLabs synthesis failed: {exc}")
            print(f"[RICO:VOICE] {text}")
