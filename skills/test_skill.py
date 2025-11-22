"""A simple test skill for demonstration purposes."""
from core.base_skill import BaseSkill


class TestSkill(BaseSkill):
    """A basic skill returning a canned test message."""

    name = "test"
    description = (
        "A debugging skill used ONLY when the user explicitly requests to run the "
        "test skill. Should not be selected for any other queries."
    )

    def run(self, *args, **kwargs):
        """Return a static message to confirm skill execution."""

        return "Test skill executed successfully."


__all__ = ["TestSkill"]
