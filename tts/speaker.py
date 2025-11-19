"""Text-to-speech playback powered by ElevenLabs and simpleaudio."""
from __future__ import annotations

import logging
import os
import pathlib
import tempfile
from typing import Optional

try:  # pragma: no cover - optional dependency
    from elevenlabs import VoiceSettings, generate, set_api_key  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    VoiceSettings = None  # type: ignore
    generate = None  # type: ignore
    set_api_key = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from simpleaudio import WaveObject  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    WaveObject = None  # type: ignore


logger = logging.getLogger(__name__)


class Speaker:
    """Handle speech synthesis and playback."""

    def __init__(self, api_key: Optional[str], voice_id: Optional[str]) -> None:
        self.api_key = api_key
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"
        if api_key and set_api_key:
            try:
                set_api_key(api_key)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to set ElevenLabs API key: %s", exc)

    def speak(self, text: str) -> None:
        """Convert text to speech and play the audio synchronously."""
        if not text:
            logger.warning("No text provided for speech synthesis.")
            return

        if not self.api_key or not generate:
            print(f"RICO (spoken): {text}")
            return

        try:
            audio_bytes = generate(
                text=text,
                voice=self.voice_id,
                model="eleven_monolingual_v1",
                voice_settings=VoiceSettings(stability=0.4, similarity_boost=0.75),
            )
        except Exception as exc:  # pragma: no cover - defensive around external call
            logger.error("ElevenLabs generation failed: %s", exc)
            print(f"RICO (spoken): {text}")
            return

        if WaveObject is None:
            logger.error("simpleaudio is not installed; cannot play audio.")
            print(f"RICO (spoken): {text}")
            return

        temp_file: pathlib.Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                temp_file = pathlib.Path(tmp.name)
                tmp.write(audio_bytes)

            wave = WaveObject.from_wave_file(str(temp_file))
            play_obj = wave.play()
            play_obj.wait_done()
        except Exception as exc:  # pragma: no cover - playback errors
            logger.error("Audio playback failed: %s", exc)
            print(f"RICO (spoken): {text}")
        finally:
            if temp_file and temp_file.exists():
                try:
                    os.remove(temp_file)
                except OSError as exc:  # pragma: no cover - best effort cleanup
                    logger.warning("Failed to remove temp audio file %s: %s", temp_file, exc)


__all__ = ["Speaker"]
