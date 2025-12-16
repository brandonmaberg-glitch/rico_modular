"""Push-to-talk audio capture for RICO."""
from __future__ import annotations

import logging
import os
import select
import sys
import time
from typing import Optional

import numpy as np

logger = logging.getLogger("RICO")


def _wait_for_enter_or_timeout(max_seconds: int) -> bool:
    """Block until Enter is pressed or the timeout elapses."""

    if os.name == "nt":
        import msvcrt  # noqa: WPS433 - Windows-specific import

        end_time = time.monotonic() + max_seconds
        while time.monotonic() < end_time:
            if msvcrt.kbhit() and msvcrt.getwch() in ("\r", "\n"):
                return True
            time.sleep(0.01)
        return False

    end_time = time.monotonic() + max_seconds
    while True:
        remaining = end_time - time.monotonic()
        if remaining <= 0:
            return False

        # Wait for Enter with a timeout so we can enforce VOICE_MAX_SECONDS.
        ready, _, _ = select.select([sys.stdin], [], [], remaining)
        if ready:
            sys.stdin.readline()
            return True


def _write_wav(
    frames: list[np.ndarray],
    *,
    channels: int,
    sample_rate: int,
    output_path: str,
) -> bool:
    """Persist the recorded frames to disk.

    Returns True on success to allow callers to gate logging and metadata.
    """

    try:
        import soundfile as sf  # type: ignore
    except Exception:
        print(
            "Audio libraries not found. Install them with: pip install sounddevice soundfile"
        )
        return False

    try:
        recording = np.concatenate(frames, axis=0) if frames else np.empty((0, channels))
        sf.write(output_path, recording, sample_rate)
    except Exception as exc:  # pragma: no cover - filesystem dependent
        logger.error("Failed to write recording: %s", exc)
        print(f"Failed to save recording: {exc}")
        return False

    return True


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
    except Exception:
        print(
            "Audio libraries not found. Install them with: pip install sounddevice soundfile"
        )
        return None

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    logger.info("Starting push-to-talk recording: %s", output_path)
    print("Recording… press Enter to stop")
    start_time = time.time()

    frames = []

    def _callback(indata, _frames, _time, status):
        if status:  # pragma: no cover - passthrough from sounddevice
            logger.warning("Recording status: %s", status)
        frames.append(indata.copy())

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            callback=_callback,
        ):
            # The sounddevice stream runs in the background; we simply block here
            # until Enter is pressed or the safety timeout fires.
            stopped_by_user = _wait_for_enter_or_timeout(max_seconds)
    except Exception as exc:  # pragma: no cover - hardware dependent
        logger.error("Recording failed: %s", exc)
        print(f"Recording failed: {exc}")
        return None

    duration = time.time() - start_time
    if stopped_by_user:
        logger.info("Stopping recording after %.2f seconds (user)", duration)
    else:
        logger.info("Stopping recording after %.2f seconds (timeout)", duration)

    if not _write_wav(frames, channels=channels, sample_rate=sample_rate, output_path=output_path):
        return None

    print(f"Stopped. Saved: {output_path} ({duration:.1f}s)")
    logger.info("Saved recording to %s (%.2fs)", output_path, duration)
    return output_path


def record_to_wav_timed(
    *,
    sample_rate: int = 16000,
    max_seconds: int = 20,
    channels: int = 1,
    output_path: str = "./tmp/input.wav",
) -> Optional[tuple[str, float]]:
    """Record audio for a fixed duration without waiting for stdin input."""

    try:
        import sounddevice as sd  # type: ignore
    except Exception:
        logger.error(
            "Audio libraries not found. Install them with: pip install sounddevice soundfile"
        )
        return None

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    frames = []

    def _callback(indata, _frames, _time, status):
        if status:  # pragma: no cover - passthrough from sounddevice
            logger.warning("Recording status: %s", status)
        frames.append(indata.copy())

    logger.info("Starting timed recording: %s", output_path)
    start_time = time.time()

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            callback=_callback,
        ):
            sd.sleep(int(max_seconds * 1000))
    except Exception as exc:  # pragma: no cover - hardware dependent
        logger.error("Recording failed: %s", exc)
        return None

    duration = time.time() - start_time
    logger.info("Timed recording finished after %.2f seconds", duration)

    if not _write_wav(frames, channels=channels, sample_rate=sample_rate, output_path=output_path):
        return None

    logger.info("Saved timed recording to %s (%.2fs)", output_path, duration)
    return output_path, duration


__all__ = ["record_to_wav", "record_to_wav_timed"]
