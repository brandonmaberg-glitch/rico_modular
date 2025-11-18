"""System status skill reporting CPU, RAM, and current time."""
from __future__ import annotations

import datetime as dt
import psutil


def activate(_: str) -> str:
    """Return formatted system statistics."""

    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory().percent
    now = dt.datetime.now().strftime("%H:%M:%S")
    return (
        f"Sir, the system is steady. CPU load sits at {cpu:.1f}% and RAM at {memory:.1f}%. "
        f"Local time is {now}."
    )
