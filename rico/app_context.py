"""Shared application context for the unified RICO runtime."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

from config.settings import AppConfig
from logs.logger import setup_logger
from router.command_router import CommandRouter
from stt.base import SpeechToTextEngine
from tts.speaker import Speaker


@dataclass
class AppContext:
    """Container for shared runtime objects that must be reused everywhere."""

    config: AppConfig
    logger: logging.Logger
    stt_engine: SpeechToTextEngine
    tts_engine: Speaker
    router: CommandRouter
    skill_registry: object
    interaction_count: int = 0


def _build_router(config: AppConfig) -> tuple[CommandRouter, object]:
    """Build the skill registry and command router once for all consumers."""

    from run_rico import build_skill_registry

    skill_registry, skills = build_skill_registry(config)
    router = CommandRouter(skills)
    return router, skill_registry


def create_app_context() -> AppContext:
    """Create the singleton-style runtime context.

    This function is only executed once (see :func:`get_app_context`) and the
    resulting objects are reused across both CLI and web execution paths.
    """

    config = AppConfig.load()
    logger = setup_logger()

    stt_engine = SpeechToTextEngine(
        config.openai_api_key,
        voice_enabled=config.voice_enabled,
        voice_key=config.voice_key,
        vad_sample_rate=config.vad_sample_rate,
        vad_max_seconds=config.vad_max_seconds,
        vad_silence_ms=config.vad_silence_ms,
        vad_aggressiveness=config.vad_aggressiveness,
        vad_pre_roll_ms=config.vad_pre_roll_ms,
        vad_min_voiced_ms=config.vad_min_voiced_ms,
    )

    tts_engine = Speaker(
        openai_api_key=config.openai_api_key,
        elevenlabs_api_key=config.elevenlabs_api_key,
        voice_id=config.elevenlabs_voice_id,
    )

    router, skill_registry = _build_router(config)

    return AppContext(
        config=config,
        logger=logger,
        stt_engine=stt_engine,
        tts_engine=tts_engine,
        router=router,
        skill_registry=skill_registry,
    )


@lru_cache(maxsize=1)
def get_app_context() -> AppContext:
    """Return the shared runtime context (created only once)."""

    return create_app_context()


__all__ = ["AppContext", "create_app_context", "get_app_context"]
