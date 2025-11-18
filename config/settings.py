"""Configuration management for RICO."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Optional


@dataclass(slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    openai_api_key: Optional[str]
    elevenlabs_api_key: Optional[str]
    elevenlabs_voice_id: Optional[str]
    log_dir: Path
    wakeword_phrase: str = "wake"

    @classmethod
    def load_from_env(cls) -> "Settings":
        """Create settings instance from OS environment variables."""

        log_dir = Path(os.getenv("RICO_LOG_DIR", "logs"))
        log_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
            log_dir=log_dir,
            wakeword_phrase=os.getenv("RICO_WAKEWORD", "wake"),
        )

    def validate(self) -> None:
        """Log warnings for missing optional but recommended secrets."""

        if not self.openai_api_key:
            print("[RICO] Warning: OPENAI_API_KEY missing. STT will use fallback mode.")
        if not self.elevenlabs_api_key:
            print("[RICO] Warning: ELEVENLABS_API_KEY missing. Speech playback disabled.")
        if self.elevenlabs_api_key and not self.elevenlabs_voice_id:
            print("[RICO] Warning: ELEVENLABS_VOICE_ID missing. Default ElevenLabs voice will be used.")
