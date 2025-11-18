"""Text helpers used throughout the assistant."""
from __future__ import annotations

import re

PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")


def clean_transcription(text: str) -> str:
    """Lowercase and strip punctuation from STT output."""
    lowered = text.lower().strip()
    return PUNCTUATION_PATTERN.sub("", lowered)


__all__ = ["clean_transcription"]
