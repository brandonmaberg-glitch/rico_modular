"""Minimal memory helpers for RICO."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

logger = logging.getLogger("RICO")

_BASE_DIR = Path(__file__).resolve().parent.parent
_LOG_DIR = _BASE_DIR / "logs"
_STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "my",
    "your",
    "our",
    "their",
    "his",
    "her",
    "me",
    "you",
    "we",
    "they",
    "them",
    "are",
    "is",
    "was",
    "were",
    "for",
    "with",
    "this",
    "that",
    "these",
    "those",
    "at",
    "in",
    "on",
    "it",
    "to",
    "of",
    "be",
}
_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:  # pragma: no cover - defensive
        logger.warning("Memory file %s is corrupt; resetting", path)
        return default


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


@dataclass
class ShortTermMemory:
    """Persist up to ``limit`` recent user messages and summarise them."""

    path: Path = field(default_factory=lambda: _LOG_DIR / "stm.json")
    limit: int = 4

    def __post_init__(self) -> None:
        self.limit = max(2, min(self.limit, 4))
        data = _load_json(self.path, default={"messages": []})
        self._messages: List[dict] = data.get("messages", [])[-self.limit :]

    def get_summary(self) -> str:
        """Return a 1–2 sentence summary of the last few user notes."""
        messages = [item.get("text", "") for item in self._messages]
        return summarise_messages(messages)

    def remember(self, text: str) -> None:
        """Store the latest user message, trimming to the configured limit."""
        cleaned = text.strip()
        if not cleaned:
            return
        self._messages.append(
            {"text": cleaned, "timestamp": datetime.utcnow().isoformat()}
        )
        self._messages = self._messages[-self.limit :]
        _write_json(self.path, {"messages": self._messages})


@dataclass
class LongTermMemory:
    """Store persistent user facts when they are deemed important."""

    path: Path = field(default_factory=lambda: _LOG_DIR / "ltm.json")
    max_entries: int = 64

    def __post_init__(self) -> None:
        data = _load_json(self.path, default={"facts": []})
        self._facts: List[dict] = data.get("facts", [])[-self.max_entries :]

    def get_relevant_facts(self, text: str, limit: int = 3) -> List[str]:
        tokens = _keyword_set(text)
        if not tokens:
            return []
        relevant: List[str] = []
        for entry in self._facts:
            fact = entry.get("fact", "")
            if not fact:
                continue
            if tokens.intersection(_keyword_set(fact)):
                relevant.append(fact)
            if len(relevant) >= limit:
                break
        return relevant

    def remember(self, fact: str) -> None:
        cleaned = fact.strip()
        if not cleaned:
            return
        # Avoid duplicates (case-insensitive comparison).
        lowered = cleaned.lower()
        for entry in self._facts:
            if entry.get("fact", "").lower() == lowered:
                return
        self._facts.append({"fact": cleaned, "timestamp": datetime.utcnow().isoformat()})
        self._facts = self._facts[-self.max_entries :]
        _write_json(self.path, {"facts": self._facts})


def summarise_messages(messages: Sequence[str]) -> str:
    """Collapse the provided user messages into <=2 light sentences."""
    cleaned: List[str] = []
    for text in messages[-4:]:
        text = re.sub(r"\s+", " ", text or "").strip()
        if text:
            cleaned.append(text)
    if not cleaned:
        return ""
    joined = "; ".join(cleaned)
    joined = joined[:280].rstrip()
    if len(cleaned) == 1:
        summary = f"Recent user note: {joined}"
    else:
        summary = f"Recent user notes: {joined}"
    if not summary.endswith("."):
        summary += "."
    return summary


def classify_long_term_fact(message: str) -> Optional[str]:
    """Return a trimmed fact string if the message has lasting value."""
    if not message or len(message) < 8:
        return None
    if re.search(r"\d{6,}", message):
        # Avoid storing serial numbers or other sensitive numeric strings.
        return None
    text = re.sub(r"\s+", " ", message).strip()
    if not text:
        return None

    lowered = text.lower()
    patterns = [
        (
            r"(?:my name is|call me)\s+([A-Za-z][A-Za-z\s]{1,40})",
            lambda m: f"The user prefers to be called {m.group(1).strip().title()}.",
        ),
        (
            r"(?:my|our)\s+car\s+(?:is|was|will be)\s+([^.?!]{3,80})",
            lambda m: f"The user's car is {m.group(1).strip().rstrip('. ')}.",
        ),
        (
            r"I\s+(?:always|usually|tend to)\s+([^.?!]{3,80})",
            lambda m: f"The user usually {m.group(1).strip().rstrip('. ')}.",
        ),
        (
            r"Every\s+(day|morning|evening|night|week)\s+([^.?!]{3,80})",
            lambda m: f"Routine note: Every {m.group(1)} {m.group(2).strip().rstrip('. ')}.",
        ),
    ]
    for pattern, formatter in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                fact = formatter(match)
            except Exception:  # pragma: no cover - defensive
                fact = match.group(0).strip()
            return _ensure_sentence(fact)

    preference = re.search(
        r"I\s+(?:really\s+)?(?:like|love|enjoy|prefer|dislike|hate)\s+([^.?!]{3,80})",
        text,
        re.IGNORECASE,
    )
    if preference:
        fact = preference.group(0).strip()
        return _ensure_sentence(fact)

    instructions = ["from now on", "always", "never", "remind me", "remember"]
    if any(token in lowered for token in instructions):
        snippet = text[:220].rsplit(" ", 1)[0] if len(text) > 220 else text
        return _ensure_sentence(snippet)

    car_keywords = ["tesla", "bmw", "audi", "mercedes", "toyota", "honda"]
    if any(word in lowered for word in car_keywords):
        return _ensure_sentence(text[:220])

    preference_keywords = ["favorite", "favourite", "prefers", "preference"]
    if any(word in lowered for word in preference_keywords):
        return _ensure_sentence(text[:220])

    return None


def _keyword_set(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    return {token for token in tokens if token not in _STOP_WORDS and len(token) > 2}


def _ensure_sentence(snippet: str) -> str:
    snippet = snippet.strip()
    if not snippet:
        return ""
    if not snippet.endswith(('.', '!')):
        snippet += "."
    return snippet


__all__ = [
    "ShortTermMemory",
    "LongTermMemory",
    "summarise_messages",
    "classify_long_term_fact",
]
