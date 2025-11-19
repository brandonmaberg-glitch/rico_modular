"""Conversation skill focused on brevity and personality."""
from __future__ import annotations

import logging
import os
from typing import Optional

from openai import OpenAI

from memory.manager import MemoryManager, load_persona, load_system_prompt

logger = logging.getLogger("RICO")

_PERSONA_ID = "rico_butler_v3"
_SYSTEM_PROMPT = load_system_prompt()
_PERSONA_TEXT = load_persona(_PERSONA_ID)
_MEMORY = MemoryManager()

_api_key = os.getenv("OPENAI_API_KEY")
_client: Optional[OpenAI] = OpenAI(api_key=_api_key) if _api_key else None


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
        _MEMORY.consider(text)
        return "Terribly sorry Sir, my conversational faculties are offline just now."

    memory_summary = _MEMORY.load_short_summary()
    system_content = f"{_SYSTEM_PROMPT}\npersona:{_PERSONA_ID}"
    persona_content = _PERSONA_TEXT

    memory_block = f"short_memory:{memory_summary}" if memory_summary else "short_memory:"

    try:
        completion = _client.chat.completions.create(
            model=_select_model(text),
            messages=[
                {"role": "system", "content": system_content},
                {"role": "system", "content": persona_content},
                {"role": "system", "content": memory_block},
                {"role": "user", "content": text},
            ],
            temperature=0.4,
        )
        choice = completion.choices[0].message.content if completion.choices else None
        if not choice:
            raise ValueError("No content returned from OpenAI response.")
        return choice.strip()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Conversation skill failed: %s", exc)
        return "My apologies Sir, my thoughts are momentarily elsewhere."
    finally:
        _MEMORY.consider(text)


__all__ = ["activate"]
