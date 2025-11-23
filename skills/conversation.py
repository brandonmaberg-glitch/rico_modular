"""Conversation skill focused on brevity and personality."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, Optional

from openai import OpenAI

from core.base_skill import BaseSkill
from utils.prompts import load_persona, load_system_prompt

logger = logging.getLogger("RICO")

description = (
    "Handles general conversation, small talk, opinions, and friendly responses "
    "when no specialised skill matches the user request."
)

_PERSONA_ID = "rico_butler_v3"
_SYSTEM_PROMPT = load_system_prompt()
_PERSONA_TEXT = load_persona(_PERSONA_ID)
_api_key = os.getenv("OPENAI_API_KEY")
_client: Optional[OpenAI] = OpenAI(api_key=_api_key) if _api_key else None

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


def _select_model(text: str) -> str:
    """Choose a lightweight model unless the request is complex."""

    lower = text.lower()
    heavy_signals = ["explain", "detailed", "why", "how", "analysis", "compare"]
    if len(text) > 260 or any(token in lower for token in heavy_signals):
        return "gpt-4.1"
    return "gpt-4.1-mini"


def activate(text: str) -> str:
    """Generate a response using minimal context."""

    if not _client:
        return "Terribly sorry Sir, my conversational faculties are offline just now."

    system_content = f"{_SYSTEM_PROMPT}\npersona:{_PERSONA_ID}"
    persona_content = _PERSONA_TEXT

    subject, subject_type = detect_subject(text)
    if subject:
        set_context_topic(subject, subject_type)
    context_message = _build_context_message() if _needs_context(text) else None

    try:
        messages = [
            {"role": "system", "content": system_content},
            {"role": "system", "content": persona_content},
        ]
        if context_message:
            messages.append(context_message)
        messages.append({"role": "user", "content": text})

        response = _client.responses.create(
            model=_select_model(text),
            input=[
                {
                    "role": message["role"],
                    "content": [{"type": "text", "text": message["content"]}],
                }
                for message in messages
            ],
            temperature=0.4,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "rico_conversation_response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "reply": {"type": "string"},
                            "memory_to_write": {"type": ["string", "null"]},
                            "should_write_memory": {"type": ["string", "null"]},
                        },
                        "required": ["reply"],
                    },
                },
            },
        )

        try:
            parsed = response.output[0].content[0].parsed  # type: ignore[index]
        except Exception:
            parsed_text = response.output_text or ""
            parsed = json.loads(parsed_text) if parsed_text else None

        if not parsed:
            raise ValueError("No parsed content returned from OpenAI response.")

        return parsed
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Conversation skill failed: %s", exc)
        return "My apologies Sir, my thoughts are momentarily elsewhere."


class ConversationSkill(BaseSkill):
    """Skill wrapper for general conversation handling."""

    name = "conversation"
    description = description

    def run(self, query: str, **kwargs) -> str:  # pylint: disable=unused-argument
        """Execute the conversation skill using existing logic."""

        return activate(query)


__all__ = [
    "activate",
    "detect_subject",
    "detect_topic",
    "get_context_subject",
    "set_context_topic",
    "ConversationSkill",
]
