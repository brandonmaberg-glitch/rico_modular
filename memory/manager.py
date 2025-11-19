"""Compact memory management for RICO.

Stores compressed bullet memories and a short rolling summary while
keeping the footprint tiny. Uses gpt-4.1-mini to decide if a user
message merits retention, falling back to lightweight heuristics when
offline.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from openai import OpenAI

logger = logging.getLogger("RICO")

_BASE_DIR = Path(__file__).resolve().parent.parent
_MEMORY_PATH = _BASE_DIR / "logs" / "memory.json"
_PERSONALITY_DIR = _BASE_DIR / "personality"
_SYSTEM_PROMPT_PATH = _BASE_DIR / "config" / "system_prompt.txt"


class MemoryManager:
    """Maintain compressed long-term notes and a short summary."""

    def __init__(self, *, max_items: int = 12, char_budget: int = 520) -> None:
        self.max_items = max(4, max_items)
        self.char_budget = max(120, char_budget)
        self._client = self._build_client()
        self._memories: List[str] = []
        self._load()

    @staticmethod
    def _build_client() -> Optional[OpenAI]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        return OpenAI(api_key=api_key)

    def _load(self) -> None:
        if not _MEMORY_PATH.exists():
            return
        try:
            with _MEMORY_PATH.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except Exception:  # pragma: no cover - defensive
            logger.warning("Memory file unreadable; starting fresh.")
            payload = {}
        self._memories = [str(item).strip() for item in payload.get("memories", []) if item]
        self._memories = self._memories[-self.max_items :]
        self._trim_to_budget()

    def _persist(self) -> None:
        _MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _MEMORY_PATH.open("w", encoding="utf-8") as file:
            json.dump({"memories": self._memories[-self.max_items :]}, file, ensure_ascii=False, indent=2)

    def _trim_to_budget(self) -> None:
        while len(" ".join(self._memories)) > self.char_budget and self._memories:
            self._memories.pop(0)

    def _condense(self, text: str) -> str:
        compact = " ".join(text.split())
        if len(compact) > 160:
            compact = compact[:157].rstrip() + "…"
        if not compact.startswith("-"):
            compact = f"- {compact}"
        return compact

    def _model_decision(self, text: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            completion = self._client.chat.completions.create(
                model="gpt-4.1-mini",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Decide if this user message is worth long-term memory. "
                            "Store only preferences, personal facts, ongoing tasks, "
                            "projects, or details the assistant should recall later. "
                            "Ignore small talk or transient mood. Respond as JSON with "
                            "store (bool) and note (<=14 words, bullet-ready)."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0,
            )
            content = completion.choices[0].message.content if completion.choices else None
            if not content:
                return None
            parsed = json.loads(content)
            if bool(parsed.get("store")):
                note = str(parsed.get("note", "")).strip()
                if note:
                    return note
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Memory classification failed: %s", exc)
        return None

    @staticmethod
    def _heuristic_note(text: str) -> Optional[str]:
        lowered = text.lower()
        triggers = ["prefer", "like", "love", "hate", "dislike", "project", "working on", "job", "car", "partner", "wife", "husband", "team", "goal", "deadline", "remember", "from now on", "always", "never"]
        if any(token in lowered for token in triggers):
            snippet = " ".join(text.strip().split())[:150]
            return snippet
        return None

    def consider(self, text: str) -> None:
        """Optionally store the user message as a compressed memory."""

        cleaned = text.strip()
        if not cleaned:
            return

        note = self._model_decision(cleaned) or self._heuristic_note(cleaned)
        if not note:
            return

        condensed = self._condense(note)
        if condensed.lower() in (item.lower() for item in self._memories):
            return
        self._memories.append(condensed)
        self._trim_to_budget()
        self._persist()

    def load_short_summary(self) -> str:
        """Return a terse memory string suitable for prompts."""

        if not self._memories:
            return ""
        recent = self._memories[-6:]
        return " | ".join(recent)


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


__all__ = ["MemoryManager", "load_persona", "load_system_prompt"]
