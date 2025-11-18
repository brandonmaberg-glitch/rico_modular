"""Intent routing for RICO skills."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional
import re

SkillHandler = Callable[[str], str]


@dataclass
class CommandRouter:
    """Match user intents to skill handlers."""

    logger: Optional[Callable[[str], None]] = None
    skills: Dict[str, SkillHandler] = field(default_factory=dict)

    def register_skill(self, name: str, handler: SkillHandler) -> None:
        """Attach a new skill handler."""

        self.skills[name] = handler
        if self.logger:
            self.logger(f"Registered skill '{name}'.")

    def route(self, text: str) -> str:
        """Route text to the appropriate skill based on pattern matching."""

        text = text or ""
        lowered = text.lower()

        if any(keyword in lowered for keyword in ["status", "system", "cpu", "memory"]):
            return self._invoke("system_status", text)
        if any(keyword in lowered for keyword in ["search", "google", "web", "look up"]):
            return self._invoke("web_search", text)
        if re.search(r"car|vehicle|ecu", lowered):
            return self._invoke("car_info", text)
        return self._invoke("conversation", text)

    def _invoke(self, skill: str, text: str) -> str:
        handler = self.skills.get(skill)
        if not handler:
            message = f"Skill '{skill}' not available."
            if self.logger:
                self.logger(message)
            return message
        try:
            return handler(text)
        except Exception as exc:  # pragma: no cover - defensive
            message = f"Skill '{skill}' failed: {exc}"
            if self.logger:
                self.logger(message)
            return message
