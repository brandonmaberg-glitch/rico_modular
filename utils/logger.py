"""Logging helpers for RICO."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logger(name: str, log_dir: Path) -> logging.Logger:
    """Create a rotating logger writing to the provided directory."""

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "rico.log"

    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.addHandler(stream_handler)
    logger.propagate = False

    return logger
