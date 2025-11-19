"""Command routing for RICO."""
from __future__ import annotations

import logging
from typing import Callable, Dict

from router.intent import IntentDecision, detect_intent

logger = logging.getLogger("RICO")


class CommandRouter:
    """LLM-first intent router."""

    def __init__(self, skills: Dict[str, Callable[[str], str]]) -> None:
        self.skills = skills

    def route(self, text: str) -> str:
        """Route text to the most appropriate skill."""

        intent: IntentDecision = detect_intent(text)
        logger.info(
            "Intent: requires_web=%s skill=%s confidence=%.2f",
            intent.requires_web,
            intent.skill,
            intent.confidence,
        )

        if intent.requires_web:
            return self.skills["web_search"](text)

        return self.skills["conversation"](text)


__all__ = ["CommandRouter"]
