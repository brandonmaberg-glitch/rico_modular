"""Placeholder for future vehicle telemetry integrations."""
from __future__ import annotations


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


__all__ = ["activate"]
