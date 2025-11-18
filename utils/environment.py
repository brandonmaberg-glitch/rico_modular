"""Utility helpers for working with environment variables."""
from __future__ import annotations

import os
from typing import Optional


def get_env_var(name: str, *, required: bool = True, default: Optional[str] = None) -> Optional[str]:
    """Fetch an environment variable with validation."""
    value = os.getenv(name, default)
    if required and not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is missing."
        )
    return value


__all__ = ["get_env_var"]
