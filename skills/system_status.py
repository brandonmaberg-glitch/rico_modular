"""System status reporting skill."""
from __future__ import annotations

import datetime

import psutil


def activate(_: str) -> str:
    """Return CPU, RAM, and current time details."""
    cpu = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory().percent
    now = datetime.datetime.now().strftime("%A %H:%M:%S")
    return (
        "Sir, system vitals are as follows: "
        f"CPU load {cpu:.1f}%, memory utilisation {memory:.1f}%, time {now}."
    )


__all__ = ["activate"]
