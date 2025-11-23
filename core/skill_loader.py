"""Utilities for discovering and loading skill classes dynamically."""

from importlib import import_module
import inspect
from pathlib import Path
from typing import List

from core.base_skill import BaseSkill


def load_skills() -> List[BaseSkill]:
    """Load all ``BaseSkill`` subclasses from the ``skills`` package.

    The function scans the repository's ``skills`` directory for Python files
    (excluding ``__init__.py``), imports each module, discovers subclasses of
    :class:`~core.base_skill.BaseSkill`, instantiates them without arguments,
    and returns the collection of instances.

    Returns:
        List[BaseSkill]: Instantiated skill objects discovered in the skills
            package.
    """

    skills_dir = Path(__file__).resolve().parent.parent / "skills"
    skill_instances: List[BaseSkill] = []

    for module_file in skills_dir.glob("*.py"):
        if module_file.name == "__init__.py":
            continue

        module_name = f"skills.{module_file.stem}"
        module = import_module(module_name)

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                # Skip ConversationSkill – it requires special construction
                if name == "ConversationSkill":
                    continue

                try:
                    # Attempt to instantiate normally
                    skill_instances.append(obj())
                except TypeError:
                    # Skip any skills requiring parameters
                    continue

    return skill_instances
