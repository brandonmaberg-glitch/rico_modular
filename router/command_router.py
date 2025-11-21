"""Command routing for RICO."""
from __future__ import annotations

import logging
from typing import Callable, Dict

from router.intent import IntentDecision, detect_intent
from ui_bridge import send_skill

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

        selected_skill = "web_search" if intent.requires_web and intent.confidence >= 0.35 else "conversation"
        send_skill(selected_skill)
        if intent.requires_web and intent.confidence >= 0.35:
            return self.skills["web_search"](text)

        return self.skills["conversation"](text)


__all__ = ["CommandRouter"]
