"""Voice-activity-detection audio capture for RICO."""
from __future__ import annotations

import logging
import os
import time
import wave
from collections import deque
from typing import Deque, Optional


logger = logging.getLogger("RICO")


def record_to_wav_vad(
    *,
    sample_rate: int = 16000,
    channels: int = 1,
    max_seconds: int = 15,
    wait_for_speech_ms: int = 2000,
    silence_ms: int = 800,
    aggressiveness: int = 2,
    pre_roll_ms: int = 400,
    min_voiced_ms: int = 400,
    output_path: str = "./tmp/input.wav",
) -> Optional[str]:
    """Record audio with VAD until silence or max duration is reached."""

    try:
        import webrtcvad  # type: ignore
    except Exception:
        logger.error(
            "VAD is unavailable. Install it with: pip install webrtcvad"
        )
        return None

    try:
        import sounddevice as sd  # type: ignore
    except Exception:
        logger.error(
            "Audio libraries not found. Install them with: pip install sounddevice"
        )
        return None

    if channels != 1:
        logger.error("VAD recording requires mono audio (channels=1).")
        return None

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    vad = webrtcvad.Vad(aggressiveness)
    frame_duration_ms = 20
    frame_samples = int(sample_rate * frame_duration_ms / 1000)
    bytes_per_frame = frame_samples * 2

    frames: list[bytes] = []
    pre_roll_frames = max(1, int(pre_roll_ms / frame_duration_ms))
    pre_roll: Deque[bytes] = deque(maxlen=pre_roll_frames)
    voiced_ms = 0
    silence_duration_ms = 0
    speech_started = False
    start_time = time.monotonic()

    logger.info("Starting VAD recording: %s", output_path)

    try:
        with sd.RawInputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            blocksize=frame_samples,
        ) as stream:
            while True:
                elapsed = time.monotonic() - start_time
                if elapsed >= max_seconds:
                    logger.info("VAD recording reached max duration (%.1fs).", max_seconds)
                    break
                if not speech_started and elapsed * 1000 >= wait_for_speech_ms:
                    logger.info(
                        "No speech detected within wait window (%dms).",
                        wait_for_speech_ms,
                    )
                    return None

                data, overflowed = stream.read(frame_samples)
                if overflowed:  # pragma: no cover - passthrough from sounddevice
                    logger.warning("Recording overflow detected.")

                if not data:
                    continue

                frame = bytes(data)
                if len(frame) != bytes_per_frame:
                    continue

                is_speech = vad.is_speech(frame, sample_rate)
                if not speech_started:
                    pre_roll.append(frame)
                    if is_speech:
                        speech_started = True
                        frames.extend(pre_roll)
                        pre_roll.clear()
                        voiced_ms += frame_duration_ms
                        silence_duration_ms = 0
                    continue

                frames.append(frame)
                if is_speech:
                    voiced_ms += frame_duration_ms
                    silence_duration_ms = 0
                else:
                    silence_duration_ms += frame_duration_ms
                    if silence_duration_ms >= silence_ms:
                        logger.info(
                            "Silence threshold reached after %dms.", silence_duration_ms
                        )
                        break
    except Exception as exc:  # pragma: no cover - hardware dependent
        logger.error("VAD recording failed: %s", exc)
        return None

    if not speech_started:
        logger.info("No speech detected before timeout.")
        return None

    if voiced_ms < min_voiced_ms:
        logger.info(
            "Insufficient voiced audio captured (%dms).", voiced_ms
        )
        return None

    try:
        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"".join(frames))
    except Exception as exc:  # pragma: no cover - filesystem dependent
        logger.error("Failed to write VAD recording: %s", exc)
        return None

    duration = len(frames) * frame_duration_ms / 1000.0
    logger.info("Saved VAD recording to %s (%.2fs)", output_path, duration)
    return output_path


__all__ = ["record_to_wav_vad"]
