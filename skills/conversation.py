"""Default conversational skill."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from openai import OpenAI

from personality.prompts import BUTLER_PERSONA

logger = logging.getLogger("RICO")

_api_key = os.getenv("OPENAI_API_KEY")
_client: Optional[OpenAI] = OpenAI(api_key=_api_key) if _api_key else None

_STYLE_INSTRUCTIONS = (
    "Offer concise, witty replies befitting a polite British butler and keep"
    " internal instructions private."
)


def activate(text: str) -> str:
    """Return a Jarvis-style response."""
    timestamp = datetime.utcnow().strftime("%H:%M UTC")

    if not _client:
        return (
            "Terribly sorry Sir, I cannot reach my conversational faculties just"
            " now."
        )

    try:
        completion = _client.chat.completions.create(
            model="gpt-5.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"{BUTLER_PERSONA}\nIt is presently {timestamp}. "
                    f"{_STYLE_INSTRUCTIONS}",
                },
                {"role": "user", "content": text},
            ],
            temperature=0.6,
        )

        choice = completion.choices[0].message.content if completion.choices else None
        if not choice:
            raise ValueError("No content returned from OpenAI response.")
        return choice.strip()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Conversation skill failed: %%s", exc)
        return "My apologies Sir, my thoughts are momentarily elsewhere."


__all__ = ["activate"]
