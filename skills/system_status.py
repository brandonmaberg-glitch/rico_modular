"""System status reporting skill."""
from __future__ import annotations

import datetime

import psutil

from core.base_skill import BaseSkill


description = (
    "Reports RICO’s internal system status, performance metrics, uptime, and "
    "subsystem health."
)


def activate(_: str) -> str:
    """Return CPU, RAM, and current time details."""
    cpu = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    now = datetime.datetime.now().strftime("%A %H:%M:%S")
    return (
        "Sir, system vitals are as follows: "
        f"CPU load {cpu:.1f}%, memory utilisation {memory:.1f}%, time {now}."
    )


class SystemStatusSkill(BaseSkill):
    """Skill wrapper for reporting system status."""

    name = "system_status"
    description = description

    def run(self, query: str, **kwargs) -> str:  # pylint: disable=unused-argument
        """Execute the system status skill using existing logic."""

        return activate(query)


__all__ = ["activate", "SystemStatusSkill"]
