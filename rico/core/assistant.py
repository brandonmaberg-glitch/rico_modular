"""Web-accessible entrypoint for the RICO assistant."""

from __future__ import annotations

import logging
from functools import lru_cache

from rico.app import RicoApp
from rico.app_context import get_app_context


class _AssistantRuntime:
    """Singleton-style runtime that mirrors the CLI pipeline."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("RICO")
        self.context = get_app_context()
        self.app = RicoApp(self.context)

    def handle_text(self, user_text: str) -> dict:
        result = self.app.handle_text(user_text, source="web")
        return {"reply": result.reply, "metadata": result.metadata}


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
