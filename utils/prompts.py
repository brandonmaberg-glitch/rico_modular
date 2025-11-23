"""Utilities for loading persona and system prompt text."""
from __future__ import annotations

from pathlib import Path
import logging

logger = logging.getLogger("RICO")

_BASE_DIR = Path(__file__).resolve().parent.parent
_PERSONALITY_DIR = _BASE_DIR / "personality"
_SYSTEM_PROMPT_PATH = _BASE_DIR / "config" / "system_prompt.txt"


def load_persona(persona_id: str) -> str:
    """Load persona details from disk."""

    path = _PERSONALITY_DIR / f"{persona_id}.txt"
    if not path.exists():
        logger.warning("Persona %s missing; using fallback.", persona_id)
        return "persona:unknown"
    return path.read_text(encoding="utf-8").strip()


def load_system_prompt() -> str:
    """Load the compressed system prompt."""

    if not _SYSTEM_PROMPT_PATH.exists():
        return ""
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


__all__ = ["load_persona", "load_system_prompt"]
