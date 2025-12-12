"""Push-to-talk audio capture for RICO."""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

logger = logging.getLogger("RICO")


def record_to_wav(
    *,
    sample_rate: int = 16000,
    max_seconds: int = 20,
    channels: int = 1,
    output_path: str = "./tmp/input.wav",
) -> Optional[str]:
    """Record audio from the default microphone and save it to a WAV file."""

    try:
        import sounddevice as sd  # type: ignore
        import soundfile as sf  # type: ignore
    except Exception:
        print(
            "Audio libraries not found. Install them with: pip install sounddevice soundfile"
        )
        return None

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    logger.info("Starting push-to-talk recording: %s", output_path)
    print("Recording… speak now")
    start_time = time.time()

    try:
        recording = sd.rec(
            int(max_seconds * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
        )
        sd.wait()
    except Exception as exc:  # pragma: no cover - hardware dependent
        logger.error("Recording failed: %s", exc)
        print(f"Recording failed: {exc}")
        return None

    duration = time.time() - start_time
    logger.info("Stopping recording after %.2f seconds", duration)

    try:
        sf.write(output_path, recording, sample_rate)
    except Exception as exc:  # pragma: no cover - filesystem dependent
        logger.error("Failed to write recording: %s", exc)
        print(f"Failed to save recording: {exc}")
        return None

    print(f"Stopped. Saved: {output_path} ({duration:.1f}s)")
    logger.info("Saved recording to %s (%.2fs)", output_path, duration)
    return output_path


__all__ = ["record_to_wav"]
