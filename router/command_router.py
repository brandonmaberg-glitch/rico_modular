"""Command routing for RICO."""
from __future__ import annotations

from typing import Callable, Dict


class CommandRouter:
    """Very small intent router based on keyword matching."""

    def __init__(self, skills: Dict[str, Callable[[str], str]]) -> None:
        self.skills = skills

    def route(self, text: str) -> str:
        """Route text to the most appropriate skill."""
        lowered = text.lower()
        if any(keyword in lowered for keyword in ["status", "cpu", "memory", "time"]):
            return self.skills["system_status"](text)
        if any(keyword in lowered for keyword in ["search", "google", "web"]):
            return self.skills["web_search"](text)
        if any(keyword in lowered for keyword in ["car", "vehicle", "ecu"]):
            return self.skills["car_info"](text)
        return self.skills["conversation"](text)


__all__ = ["CommandRouter"]
