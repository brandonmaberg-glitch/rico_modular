"""Simple placeholder wakeword detection engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


def sanitize_text(value: str) -> str:
    """Normalize user input for reliable matching."""

    return value.strip().lower()


class WakewordCallback(Protocol):
    """Protocol for functions invoked after wakeword detection."""

    def __call__(self) -> None:  # pragma: no cover - interface definition
        ...


@dataclass
class WakewordEngine:
    """Placeholder wakeword engine driven via console input."""

    wakeword: str

    def detect_wakeword(self) -> bool:
        """Return True when the user types the configured wakeword."""

        try:
            user_entry = input(f"Type '{self.wakeword}' to wake RICO (or 'quit'): ")
        except EOFError:
            return False

        normalized = sanitize_text(user_entry)
        if normalized == "quit":
            raise KeyboardInterrupt
        return normalized == sanitize_text(self.wakeword)
