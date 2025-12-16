"""Web-accessible entrypoint for the RICO assistant."""

from __future__ import annotations

import logging
from functools import lru_cache

from config.settings import AppConfig
from logs.logger import setup_logger
from router.command_router import CommandRouter
from run_rico import build_skill_registry, handle_text_interaction


class _AssistantRuntime:
    """Singleton-style runtime that mirrors the CLI pipeline."""

    def __init__(self) -> None:
        self.config = AppConfig.load()
        self.logger = logging.getLogger("RICO")
        setup_logger()
        skill_registry, skills = build_skill_registry(self.config)
        self.skill_registry = skill_registry
        self.router = CommandRouter(skills)
        self.interaction_count = 0

    def handle_text(self, user_text: str) -> dict:
        self.interaction_count += 1
        return handle_text_interaction(
            user_text=user_text,
            router=self.router,
            skill_registry=self.skill_registry,
            interaction_count=self.interaction_count,
        )


@lru_cache(maxsize=1)
def _get_runtime() -> _AssistantRuntime:
    return _AssistantRuntime()


def handle_text(user_text: str) -> dict:
    """Process text via the existing RICO pipeline and return reply metadata."""

    cleaned = user_text.strip()
    if not cleaned:
        return {"reply": "Please provide a command, Sir.", "metadata": {}}

    runtime = _get_runtime()
    return runtime.handle_text(cleaned)


__all__ = ["handle_text"]
