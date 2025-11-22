from typing import Dict, List

from core.base_skill import BaseSkill


class SkillRegistry:
    """Registry for managing BaseSkill instances."""

    def __init__(self) -> None:
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """Register a skill instance.

        Args:
            skill: An instance of BaseSkill to register.

        Raises:
            TypeError: If ``skill`` is not an instance of BaseSkill.
        """
        if not isinstance(skill, BaseSkill):
            raise TypeError("skill must be an instance of BaseSkill")

        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill | None:
        """Retrieve a registered skill by name."""
        return self._skills.get(name)

    def all(self) -> List[BaseSkill]:
        """Return all registered skills."""
        return list(self._skills.values())
