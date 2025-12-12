"""Configuration management for the RICO assistant."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from utils.environment import get_env_var

load_dotenv()


@dataclass(slots=True)
class AppConfig:
    """Central configuration for the RICO runtime."""

    openai_api_key: Optional[str]
    elevenlabs_api_key: Optional[str]
    elevenlabs_voice_id: Optional[str]
    ddg_safe_search: bool
    voice_enabled: bool
    voice_key: str
    voice_sample_rate: int
    voice_max_seconds: int

    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration from the environment with validation."""
        openai_api_key = get_env_var("OPENAI_API_KEY", required=False)
        elevenlabs_api_key = get_env_var("ELEVENLABS_API_KEY", required=False)
        elevenlabs_voice_id = get_env_var("ELEVENLABS_VOICE_ID", required=False)
        ddg_safe_search = get_env_var("DDG_SAFE_SEARCH", required=False, default="true")
        voice_enabled = get_env_var("VOICE_ENABLED", required=False, default="false")
        voice_key = get_env_var("VOICE_KEY", required=False, default="v")
        voice_sample_rate = get_env_var("VOICE_SAMPLE_RATE", required=False, default="16000")
        voice_max_seconds = get_env_var("VOICE_MAX_SECONDS", required=False, default="20")

        return cls(
            openai_api_key=openai_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            elevenlabs_voice_id=elevenlabs_voice_id,
            ddg_safe_search=ddg_safe_search.lower() in {"1", "true", "yes"},
            voice_enabled=voice_enabled.lower() in {"1", "true", "yes"},
            voice_key=voice_key or "v",
            voice_sample_rate=int(voice_sample_rate or 16000),
            voice_max_seconds=int(voice_max_seconds or 20),
        )


__all__ = ["AppConfig"]
