"""Logging helpers for RICO."""
from __future__ import annotations

import logging
import pathlib
from typing import Optional

LOG_FILE = pathlib.Path("logs/rico.log")


def setup_logger(name: str = "RICO", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


__all__ = ["setup_logger"]
