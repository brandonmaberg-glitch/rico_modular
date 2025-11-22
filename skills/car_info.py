"""Placeholder for future vehicle telemetry integrations."""
from __future__ import annotations

from core.base_skill import BaseSkill


description = (
    "Provides information about the car’s engine status, diagnostics, performance, "
    "health checks, and sensor readings."
)


def activate(_: str) -> str:
    """Return a stub response describing future capabilities."""
    return (
        "Mr Berg, the vehicle telemetry module is standing by for integration with "
        "the ECU. For now I can only log your request."
    )


class CarInfoSkill(BaseSkill):
    """Skill wrapper for car information retrieval."""

    name = "car_info"
    description = description

    def run(self, query: str, **kwargs) -> str:  # pylint: disable=unused-argument
        """Execute the car info skill using existing logic."""

        return activate(query)


__all__ = ["activate", "CarInfoSkill"]
