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
        if any(
            phrase in lowered
            for phrase in [
                "what's the time",
                "whats the time",
                "what is the time",
                "tell me the time",
                "current time",
                "local time",
                "time is it",
            ]
        ):
            return self.skills["conversation"](text)
        if any(
            keyword in lowered
            for keyword in ["system status", "system info", "cpu", "processor", "memory", "memory usage", "system vitals", "performance"]
        ):
            return self.skills["system_status"](text)
        if any(keyword in lowered for keyword in ["search", "google", "web"]):
            return self.skills["web_search"](text)
        if any(
            pattern in lowered
            for pattern in ["who is", "what is", "what happened", "why did", "lookup", "google", "search"]
        ):
            return self.skills["web_search"](text)
        if any(keyword in lowered for keyword in ["car", "vehicle", "ecu"]):
            return self.skills["car_info"](text)
        return self.skills["conversation"](text)


__all__ = ["CommandRouter"]
