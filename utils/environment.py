"""Utility helpers for working with environment variables."""
from __future__ import annotations

import os
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("RICO")

def get_env_var(name: str, *, required: bool = True, default: Optional[str] = None) -> Optional[str]:
    """Fetch an environment variable with validation."""
    load_dotenv()

    value = os.getenv(name)
    if not value:
        if default is not None:
            logger.info("Environment variable %s not set; using default.", name)
            return default
        if required:
            logger.warning("Environment variable %s is missing and required.", name)
            raise EnvironmentError(
                f"Required environment variable '{name}' is missing."
            )
        logger.info("Environment variable %s is missing; returning None.", name)
        return None
    return value


__all__ = ["get_env_var"]
