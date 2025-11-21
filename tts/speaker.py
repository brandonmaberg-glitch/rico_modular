"""Text-to-speech playback using OpenAI and ElevenLabs with playsound3."""
from __future__ import annotations

import logging
import os
import pathlib
import tempfile
from typing import Optional

try:  # pragma: no cover - optional dependency
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import playsound3  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    playsound3 = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from elevenlabs import ElevenLabs, VoiceSettings  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ElevenLabs = None  # type: ignore
    VoiceSettings = None  # type: ignore


logger = logging.getLogger(__name__)


class Speaker:
    """Handle speech synthesis and synchronous playback."""

    def __init__(
        self,
        openai_api_key: Optional[str],
        elevenlabs_api_key: Optional[str],
        voice_id: Optional[str],
    ) -> None:
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"
        self._openai_client: Optional[OpenAI] = None
        self._elevenlabs_client: Optional[ElevenLabs] = None
        self._provider: str = "text"

        if openai_api_key and OpenAI:
            try:
                self._openai_client = OpenAI(api_key=openai_api_key)
                self._provider = "openai"
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to initialise OpenAI client: %s", exc)

        self.elevenlabs_api_key = elevenlabs_api_key
        if elevenlabs_api_key and ElevenLabs:
            try:
                self._elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)
                if self._provider == "text":
                    self._provider = "elevenlabs"
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to initialise ElevenLabs client: %s", exc)

    @property
    def provider(self) -> str:
        """Return the active voice provider."""

        return self._provider

    def switch_to_elevenlabs(self) -> bool:
        """Switch to ElevenLabs playback if credentials exist."""

        if not (self._elevenlabs_client and self.elevenlabs_api_key):
            logger.warning("Cannot switch to ElevenLabs: missing API key or SDK.")
            return False

        self._provider = "elevenlabs"
        return True

    def switch_to_openai(self) -> bool:
        """Switch to OpenAI playback if credentials exist."""

        if not self._openai_client:
            logger.warning("Cannot switch to OpenAI: client is not initialised.")
            return False

        self._provider = "openai"
        return True

    def speak(self, text: str) -> None:
        """Convert text to speech and play the audio synchronously."""
        if not text:
            logger.warning("No text provided for speech synthesis.")
            return

        audio_bytes: Optional[bytes] = None
        if self._provider == "openai":
            audio_bytes = self._speak_openai(text)
        elif self._provider == "elevenlabs":
            audio_bytes = self._speak_elevenlabs(text)

        if audio_bytes is None:
            print(f"RICO (spoken): {text}")
            return

        if playsound3 is None:
            logger.error("playsound3 is not installed; cannot play audio.")
            print(f"RICO (spoken): {text}")
            return

        temp_file: pathlib.Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                temp_file = pathlib.Path(tmp.name)
                tmp.write(audio_bytes)

            try:
                playsound3.playsound(str(temp_file), block=True)
            except Exception as exc:  # pragma: no cover - playback errors
                logger.error("Audio playback failed: %s", exc)
                print("Apologies, I couldn't play that audio, but I'll keep going.")
                print(f"RICO (spoken): {text}")
        finally:
            if temp_file and temp_file.exists():
                try:
                    os.remove(temp_file)
                except OSError as exc:  # pragma: no cover - best effort cleanup
                    logger.warning("Failed to remove temp audio file %s: %s", temp_file, exc)

    def _speak_openai(self, text: str) -> Optional[bytes]:
        """Generate speech audio using OpenAI TTS."""

        if not self._openai_client:
            logger.warning("OpenAI client unavailable; falling back to text output.")
            return None

        try:
            with self._openai_client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=text,
                response_format="wav",
            ) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - defensive around external call
            logger.error("OpenAI TTS generation failed: %s", exc)
            return None

    def _speak_elevenlabs(self, text: str) -> Optional[bytes]:
        """Generate speech audio using ElevenLabs TTS."""

        if not self._elevenlabs_client:
            logger.warning("ElevenLabs client unavailable; falling back to text output.")
            return None

        try:
            voice_settings = None
            if VoiceSettings:
                voice_settings = VoiceSettings(stability=0.4, similarity_boost=0.75)

            response = self._elevenlabs_client.text_to_speech.convert(
                voice_id=self.voice_id,
                model_id="eleven_monolingual_v1",
                text=text,
                voice_settings=voice_settings,
                output_format="wav",
            )
            audio_bytes = b"".join(chunk for chunk in response if chunk)
            if not audio_bytes:
                logger.error("ElevenLabs returned an empty audio response.")
                return None
            return audio_bytes
        except Exception as exc:  # pragma: no cover - defensive around external call
            logger.error("ElevenLabs generation failed: %s", exc)
            return None


__all__ = ["Speaker"]
