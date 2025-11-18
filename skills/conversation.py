"""Default conversational skill."""
from __future__ import annotations

from datetime import datetime

from personality.prompts import BUTLER_PERSONA


def activate(text: str) -> str:
    """Return a Jarvis-style response."""
    timestamp = datetime.utcnow().strftime("%H:%M UTC")
    return (
        f"{BUTLER_PERSONA} It is presently {timestamp}. "
        f"You said: '{text}'. How else may I serve you, Sir?"
    )


__all__ = ["activate"]
