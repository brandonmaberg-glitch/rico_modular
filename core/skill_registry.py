from typing import Dict, List, Type

from core.base_skill import BaseSkill


class SkillRegistry:
    """Registry for managing BaseSkill subclasses."""

    def __init__(self) -> None:
        self._skills: Dict[str, Type[BaseSkill]] = {}

    def register(self, skill_class: Type[BaseSkill]) -> None:
        """Register a skill class.

        Args:
            skill_class: A subclass of BaseSkill to register.

        Raises:
            TypeError: If ``skill_class`` is not a subclass of BaseSkill.
        """
        if not issubclass(skill_class, BaseSkill):
            raise TypeError("skill_class must be a subclass of BaseSkill")

        self._skills[skill_class.__name__] = skill_class

    def get(self, name: str) -> Type[BaseSkill] | None:
        """Retrieve a registered skill class by name."""
        return self._skills.get(name)

    def all(self) -> List[Type[BaseSkill]]:
        """Return all registered skill classes."""
        return list(self._skills.values())
