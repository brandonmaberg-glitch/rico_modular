from dotenv import load_dotenv
load_dotenv()
"""Configuration management for the RICO assistant."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from utils.environment import get_env_var


@dataclass(slots=True)
class AppConfig:
    """Central configuration for the RICO runtime."""

    openai_api_key: Optional[str]
    elevenlabs_api_key: Optional[str]
    elevenlabs_voice_id: Optional[str]
    ddg_safe_search: bool

    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration from the environment with validation."""
        openai_api_key = get_env_var("OPENAI_API_KEY", required=False)
        elevenlabs_api_key = get_env_var("ELEVENLABS_API_KEY", required=False)
        elevenlabs_voice_id = get_env_var("ELEVENLABS_VOICE_ID", required=False)
        ddg_safe_search = get_env_var("DDG_SAFE_SEARCH", required=False, default="true")

        return cls(
            openai_api_key=openai_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            elevenlabs_voice_id=elevenlabs_voice_id,
            ddg_safe_search=ddg_safe_search.lower() in {"1", "true", "yes"},
        )


__all__ = ["AppConfig"]
