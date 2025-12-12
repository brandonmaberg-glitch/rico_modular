"""WAV transcription helper using the OpenAI SDK."""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

from openai import OpenAI

logger = logging.getLogger("RICO")


def _get_client() -> Optional[OpenAI]:
    """Reuse the shared OpenAI client if available, otherwise create one."""

    try:
        from conversation import _client as conversation_client
    except Exception:  # pragma: no cover - defensive import guard
        conversation_client = None

    if conversation_client:
        return conversation_client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        return OpenAI(api_key=api_key)
    except Exception:  # pragma: no cover - defensive
        return None


def transcribe_wav(path: str) -> str:
    """Transcribe a WAV file and return cleaned text."""

    client = _get_client()
    if not client:
        print("OpenAI client unavailable. Set OPENAI_API_KEY to enable voice input.")
        return ""

    if not os.path.exists(path):
        print(f"Recording not found at {path}")
        return ""

    logger.info("Starting transcription for %s", path)
    start_time = time.time()
    try:
        with open(path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
            )
    except Exception as exc:  # pragma: no cover - network dependent
        logger.error("Transcription failed: %s", exc)
        print(f"Transcription failed: {exc}")
        return ""

    duration = time.time() - start_time
    logger.info("Finished transcription in %.2fs", duration)

    text = getattr(response, "text", "") or ""
    return text.strip()


__all__ = ["transcribe_wav"]
