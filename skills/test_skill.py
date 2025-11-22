"""A simple test skill for demonstration purposes."""
from core.base_skill import BaseSkill


class TestSkill(BaseSkill):
    """A basic skill returning a canned test message."""

    name = "test"
    description = "Return a static test response."

    def run(self, *args, **kwargs):
        """Return a static message to confirm skill execution."""

        return "Test skill executed successfully."


__all__ = ["TestSkill"]
