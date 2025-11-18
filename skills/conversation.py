"""Default conversational skill."""
from __future__ import annotations

from personality.prompts import JARVIS_PROMPT


def activate(text: str) -> str:
    """Return a witty Jarvis-style response."""

    if not text:
        return "Sir, I am standing by whenever you require me."

    return (
        f"{JARVIS_PROMPT} You said: '{text}'. Allow me to assist: Sir, "
        "perhaps we should explore that in more detail once the full AI stack is online."
    )
