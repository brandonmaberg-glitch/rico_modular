"""LLM-powered intent detection for routing."""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

logger = logging.getLogger("RICO")


@dataclass
class IntentDecision:
    """Structured intent prediction returned by the classifier."""

    requires_web: bool
    skill: str
    confidence: float


_CLIENT: Optional[OpenAI] = None

_INTENT_PROMPT = (
    "Classify the user request for RICO. Use comprehension, not keywords."
)

_GUIDELINES = (
    "Reply as JSON with requires_web (bool), skill (web_search or conversation),"
    " confidence (0-1). requires_web only when the user clearly needs current,"
    " external facts such as prices, weather, scores, fresh news, or ongoing"
    " events. For feelings, opinions, advice, creative work, or questions about"
    " RICO, keep requires_web false."
)


def _is_image_request(text: str) -> bool:
    lowered = text.lower()
    direct_phrases = (
        "show me a picture",
        "look up a picture",
        "show me an image",
    )
    if any(phrase in lowered for phrase in direct_phrases):
        return True

    if re.search(r"\b(picture|image) of\s+(him|her|them|it)\b", lowered):
        return True

    if re.search(r"what does\s+(he|she|they|it)\s+look like", lowered):
        return True

    return False


def _get_client() -> Optional[OpenAI]:
    """Return a cached OpenAI client if credentials are present."""

    global _CLIENT  # pylint: disable=global-statement

    if _CLIENT is not None:
        return _CLIENT

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    _CLIENT = OpenAI(api_key=api_key)
    return _CLIENT


def detect_intent(text: str) -> IntentDecision:
    """Classify the user's message using an LLM."""

    default = IntentDecision(requires_web=False, skill="conversation", confidence=0.0)

    if _is_image_request(text):
        return IntentDecision(
            requires_web=True,
            skill="web_search",
            confidence=0.95,
        )

    client = _get_client()

    if not client:
        logger.warning("Intent detection unavailable; defaulting to conversation.")
        return default

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _INTENT_PROMPT},
                {"role": "system", "content": _GUIDELINES},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
        content = completion.choices[0].message.content if completion.choices else None
        if not content:
            raise ValueError("No content returned from intent classifier.")

        parsed = json.loads(content)
        requires_web = bool(parsed.get("requires_web", False))
        skill = str(parsed.get("skill", "conversation"))
        confidence = float(parsed.get("confidence", 0.0))

        if skill not in {"web_search", "conversation"}:
            skill = "web_search" if requires_web else "conversation"

        return IntentDecision(
            requires_web=requires_web,
            skill=skill,
            confidence=max(0.0, min(confidence, 1.0)),
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Intent detection failed: %s", exc)
        return default


__all__ = ["detect_intent", "IntentDecision"]
