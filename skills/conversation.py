"""Conversation skill focused on brevity and personality."""
from __future__ import annotations

import logging
import re
from typing import Dict, Optional

from core.base_skill import BaseSkill
from utils.prompts import load_persona, load_system_prompt
from run_rico import _conversation_with_memory

logger = logging.getLogger("RICO")

description = (
    "Handles general conversation, small talk, opinions, and friendly responses "
    "when no specialised skill matches the user request."
)

_PERSONA_ID = "rico_butler_v3"
_SYSTEM_PROMPT = load_system_prompt()
_PERSONA_TEXT = load_persona(_PERSONA_ID)
_CONTEXT: Dict[str, Optional[str]] = {
    "last_subject": None,
    "last_subject_type": None,
}


def _extract_subject(text: str) -> tuple[Optional[str], Optional[str]]:
    """Lightweight subject detection to avoid full history usage."""

    lowered = text.lower()
    trigger_phrases = [
        ("who is", "person"),
        ("who was", "person"),
        ("tell me about", "person"),
        ("what is", "thing"),
        ("where is", "place"),
        ("what do you know about", "thing"),
        ("give me info on", "thing"),
        ("describe", "thing"),
        ("picture of", "thing"),
        ("image of", "thing"),
    ]
    for phrase, subject_type in trigger_phrases:
        if phrase in lowered:
            start = lowered.find(phrase) + len(phrase)
            subject = text[start:].strip(" ?.,!\"")
            if subject:
                subject_lower = subject.lower()
                pronouns = {"he", "she", "they", "him", "her", "them", "it", "this", "that"}
                if subject_lower in pronouns:
                    return None, None
                return subject, subject_type or "thing"

    match = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", text)
    if match:
        return match.group(1), "person"

    return None, None


def _needs_context(text: str) -> bool:
    lowered = text.lower()
    pronouns_pattern = r"\b(he|she|they|him|her|them|it|this|that)\b"
    has_pronoun = bool(re.search(pronouns_pattern, lowered))
    return has_pronoun and bool(_CONTEXT.get("last_subject"))


def set_context_topic(topic: Optional[str], subject_type: Optional[str] = None) -> None:
    """Persist the most recent topic for light-weight follow ups."""

    cleaned = topic.strip() if topic else None
    _CONTEXT["last_subject"] = cleaned or None
    if cleaned:
        _CONTEXT["last_subject_type"] = subject_type or "thing"
    else:
        _CONTEXT["last_subject_type"] = None


def detect_topic(text: str) -> Optional[str]:
    """Expose subject extraction so other skills can keep context fresh."""

    subject, _ = _extract_subject(text)
    return subject


def detect_subject(text: str) -> tuple[Optional[str], Optional[str]]:
    """Return the detected subject and its type if present."""

    return _extract_subject(text)


def get_context_subject() -> tuple[Optional[str], Optional[str]]:
    """Return the last stored subject and its type."""

    return _CONTEXT.get("last_subject"), _CONTEXT.get("last_subject_type")


def _build_context_message() -> Optional[dict]:
    subject = _CONTEXT.get("last_subject")
    if not subject:
        return None
    return {"role": "system", "content": f"Context: The user is referring to {subject}."}


def activate(text: str) -> str:
    return _conversation_with_memory(text)


class ConversationSkill(BaseSkill):
    """Skill wrapper for general conversation handling."""

    name = "conversation"
    description = description

    def run(self, query: str, **kwargs) -> str:  # pylint: disable=unused-argument
        """Execute the conversation skill using existing logic."""

        return _conversation_with_memory(query)


__all__ = [
    "activate",
    "detect_subject",
    "detect_topic",
    "get_context_subject",
    "set_context_topic",
    "ConversationSkill",
]
