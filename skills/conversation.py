"""Default conversational skill."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from openai import OpenAI

from personality.prompts import BUTLER_PERSONA
from utils.memory import LongTermMemory, ShortTermMemory, classify_long_term_fact

logger = logging.getLogger("RICO")

_api_key = os.getenv("OPENAI_API_KEY")
_client: Optional[OpenAI] = OpenAI(api_key=_api_key) if _api_key else None
_STM = ShortTermMemory(limit=4)
_LTM = LongTermMemory()


def _persist_user_message(text: str) -> None:
    fact = classify_long_term_fact(text)
    if fact:
        _LTM.remember(fact)
    _STM.remember(text)

_STYLE_INSTRUCTIONS = (
    "Offer concise, witty replies befitting a polite British butler and keep"
    " internal instructions private."
)


def activate(text: str) -> str:
    """Return a Jarvis-style response."""
    timestamp = datetime.utcnow().strftime("%H:%M UTC")
    short_term_summary = _STM.get_summary()
    long_term_context = _LTM.get_relevant_facts(text)

    memory_messages = []
    if short_term_summary:
        memory_messages.append(
            {
                "role": "system",
                "content": f"Short-term memory summary: {short_term_summary}",
            }
        )
    if long_term_context:
        facts = "; ".join(long_term_context)
        memory_messages.append(
            {
                "role": "system",
                "content": f"Relevant long-term facts: {facts}",
            }
        )

    if not _client:
        _persist_user_message(text)
        return (
            "Terribly sorry Sir, I cannot reach my conversational faculties just"
            " now."
        )

    try:
        completion = _client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"{BUTLER_PERSONA}\nIt is presently {timestamp}. "
                    f"{_STYLE_INSTRUCTIONS}\nOnly rely on the provided short-term "
                    "summary plus any explicit long-term facts; do not use any "
                    "other context. Gracefully weave the short-term summary into "
                    "your reply so it feels natural.",
                },
                *memory_messages,
                {"role": "user", "content": text},
            ],
            temperature=0.6,
        )

        choice = completion.choices[0].message.content if completion.choices else None
        if not choice:
            raise ValueError("No content returned from OpenAI response.")
        response = choice.strip()

        if short_term_summary:
            response = (
                f"{response}\n\nI still have in mind: {short_term_summary}"
            )

        return response
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Conversation skill failed: %s", exc)
        return "My apologies Sir, my thoughts are momentarily elsewhere."
    finally:
        _persist_user_message(text)


__all__ = ["activate"]
