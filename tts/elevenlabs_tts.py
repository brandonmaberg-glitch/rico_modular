"""ElevenLabs text-to-speech integration."""
from __future__ import annotations

import pathlib
from typing import Optional

try:
    from elevenlabs import VoiceSettings, generate, set_api_key  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    VoiceSettings = None  # type: ignore
    generate = None  # type: ignore
    set_api_key = None  # type: ignore


class ElevenLabsTTS:
    """Wrapper around the ElevenLabs API with graceful fallbacks."""

    def __init__(self, api_key: Optional[str], voice_id: Optional[str]) -> None:
        self.api_key = api_key
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"
        if api_key and set_api_key:
            try:
                set_api_key(api_key)
            except Exception:
                pass

    def speak(self, text: str, *, save_path: pathlib.Path | None = None) -> None:
        """Convert text to speech, falling back to console output."""
        if self.api_key and generate:
            try:
                audio = generate(
                    text=text,
                    voice=self.voice_id,
                    model="eleven_monolingual_v1",
                    voice_settings=VoiceSettings(stability=0.4, similarity_boost=0.75),
                )
                target = save_path or pathlib.Path("tts_output.mp3")
                target.write_bytes(audio)
                print(f"[TTS] Audio saved to {target}")
                return
            except Exception as exc:  # pragma: no cover
                print(f"[TTS] ElevenLabs call failed: {exc}")

        print(f"RICO (spoken): {text}")


__all__ = ["ElevenLabsTTS"]
