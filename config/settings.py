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
    vad_sample_rate: int
    vad_max_seconds: int
    vad_silence_ms: int
    vad_aggressiveness: int
    vad_pre_roll_ms: int
    vad_min_voiced_ms: int

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
        vad_sample_rate = get_env_var("VAD_SAMPLE_RATE", required=False, default="16000")
        vad_max_seconds = get_env_var("VAD_MAX_SECONDS", required=False, default="15")
        vad_silence_ms = get_env_var("VAD_SILENCE_MS", required=False, default="800")
        vad_aggressiveness = get_env_var("VAD_AGGRESSIVENESS", required=False, default="2")
        vad_pre_roll_ms = get_env_var("VAD_PRE_ROLL_MS", required=False, default="400")
        vad_min_voiced_ms = get_env_var("VAD_MIN_VOICED_MS", required=False, default="400")

        return cls(
            openai_api_key=openai_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            elevenlabs_voice_id=elevenlabs_voice_id,
            ddg_safe_search=ddg_safe_search.lower() in {"1", "true", "yes"},
            voice_enabled=voice_enabled.lower() in {"1", "true", "yes"},
            voice_key=voice_key or "v",
            voice_sample_rate=int(voice_sample_rate or 16000),
            voice_max_seconds=int(voice_max_seconds or 20),
            vad_sample_rate=int(vad_sample_rate or 16000),
            vad_max_seconds=int(vad_max_seconds or 15),
            vad_silence_ms=int(vad_silence_ms or 800),
            vad_aggressiveness=int(vad_aggressiveness or 2),
            vad_pre_roll_ms=int(vad_pre_roll_ms or 400),
            vad_min_voiced_ms=int(vad_min_voiced_ms or 400),
        )


__all__ = ["AppConfig"]
