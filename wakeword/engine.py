"""Placeholder wakeword engine for RICO."""
from __future__ import annotations

import time
from typing import Optional


class WakeWordEngine:
    """Simple text-based wakeword detector."""

    def __init__(self, wakeword: str = "wake") -> None:
        self.wakeword = wakeword.lower()

    def wait_for_wakeword(self) -> bool:
        """Block until the user types the wakeword."""
        try:
            user_input = input("Type 'wake' to start interacting with RICO: ")
        except (EOFError, KeyboardInterrupt):
            return False
        return user_input.strip().lower() == self.wakeword


__all__ = ["WakeWordEngine"]
