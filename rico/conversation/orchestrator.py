"""Centralized conversation orchestration for CLI and Web UI."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any

from rico.app import RicoApp
from rico.app_context import AppContext
from rico.voice.transcribe import transcribe_wav
from rico.voice.vad_input import record_to_wav_vad
from stt.base import TranscriptionResult


FOLLOWUP_TIMEOUT_MS = 6000
SECOND_CHANCE_TIMEOUT_MS = 3000
DEFAULT_MANUAL_TIMEOUT_MS = 20000

ACKNOWLEDGEMENT_PHRASES = {
    "ok",
    "okay",
    "yeah",
    "yep",
    "nah",
    "nice",
    "cool",
    "cheers",
    "thanks",
    "thank you",
    "lol",
    "haha",
    "alright",
    "sound",
    "safe",
    "right",
}

GREETING_PHRASES = {
    "hallo",
    "hello",
    "hi",
    "hey",
    "hiya",
    "good morning",
    "good afternoon",
    "good evening",
}

QUESTION_STARTERS = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "can",
    "could",
    "should",
    "would",
    "do",
    "did",
    "is",
    "are",
)

logger = logging.getLogger(__name__)


@dataclass
class TurnResult:
    """Structured output for a single conversation turn."""

    transcript: str
    reply: str
    replied: bool
    should_followup: bool
    followup_timeout_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)


def _normalize_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return re.sub(r"[^\w\s]", "", normalized)


def _should_respond_with_reason(text: str) -> tuple[bool, str | None]:
    """Return True when a reply is warranted for the provided text."""

    if not text or not text.strip():
        return False, "empty"

    normalized = _normalize_text(text)
    if not normalized:
        return False, "empty"

    if normalized in ACKNOWLEDGEMENT_PHRASES:
        return False, "ack"

    if normalized in GREETING_PHRASES:
        return True, None

    words = re.findall(r"\b\w+\b", normalized)
    if len(words) <= 2 and "?" not in text:
        return False, "short_non_question"

    if "?" in text:
        return True, None

    if re.match(rf"^({'|'.join(QUESTION_STARTERS)})\b", normalized) is not None:
        return True, None

    return False, "short_non_question"


def should_respond(text: str) -> bool:
    respond, _reason = _should_respond_with_reason(text)
    return respond


def _is_acknowledgement(text: str) -> bool:
    normalized = _normalize_text(text)
    return normalized in ACKNOWLEDGEMENT_PHRASES


def _build_turn_result(
    *,
    transcript: str,
    reply: str,
    metadata: dict[str, Any],
    should_followup: bool,
    followup_timeout_ms: int,
) -> TurnResult:
    replied = bool(reply.strip())
    return TurnResult(
        transcript=transcript,
        reply=reply,
        replied=replied,
        should_followup=should_followup,
        followup_timeout_ms=followup_timeout_ms,
        metadata=metadata,
    )


def process_text_turn(
    rico_app: RicoApp,
    context: AppContext,
    text: str,
    source: str,
) -> TurnResult:
    """Process a single text turn using shared gating and response handling."""

    cleaned = text.strip()
    metadata: dict[str, Any] = {"source": source, "mode": "text"}

    if not cleaned:
        metadata["error"] = "no_text"
        logger.info(
            "orchestrator: gated transcript=%r mode=%s reason=%s",
            cleaned,
            "text",
            "empty",
        )
        return _build_turn_result(
            transcript="",
            reply="",
            metadata=metadata,
            should_followup=False,
            followup_timeout_ms=0,
        )

    if _is_acknowledgement(cleaned):
        metadata["gated"] = True
        metadata["gated_reason"] = "ack"
        logger.info(
            "orchestrator: gated transcript=%r mode=%s reason=%s",
            cleaned,
            "text",
            "ack",
        )
        return _build_turn_result(
            transcript=cleaned,
            reply="",
            metadata=metadata,
            should_followup=False,
            followup_timeout_ms=0,
        )

    response = rico_app.handle_text(cleaned, source=source)
    reply = response.reply or ""
    metadata.update(response.metadata or {})
    metadata.setdefault("source", source)
    metadata["mode"] = "text"

    return _build_turn_result(
        transcript=cleaned,
        reply=reply,
        metadata=metadata,
        should_followup=False,
        followup_timeout_ms=0,
    )


def _transcribe_cli(
    context: AppContext,
    timeout_ms: int | None,
) -> tuple[str, dict[str, Any]]:
    timeout_sec = timeout_ms / 1000 if timeout_ms else None
    transcription = context.stt_engine.transcribe(timeout=timeout_sec)
    if isinstance(transcription, TranscriptionResult):
        result = transcription
    else:  # pragma: no cover - defensive for legacy return
        result = TranscriptionResult(text=str(transcription), timed_out=False)

    if result.timed_out:
        return "", {"timed_out": True, "error": "timeout"}

    return result.text.strip(), {}


def _transcribe_web(
    context: AppContext,
    timeout_ms: int | None,
) -> tuple[str, dict[str, Any]]:
    timeout_sec = timeout_ms / 1000 if timeout_ms else context.config.vad_max_seconds
    max_seconds = min(context.config.vad_max_seconds, timeout_sec)

    output_path = record_to_wav_vad(
        sample_rate=context.config.vad_sample_rate,
        max_seconds=max_seconds,
        silence_ms=context.config.vad_silence_ms,
        aggressiveness=context.config.vad_aggressiveness,
        pre_roll_ms=context.config.vad_pre_roll_ms,
        min_voiced_ms=context.config.vad_min_voiced_ms,
    )
    if not output_path:
        return "", {"error": "no_speech"}

    transcript = transcribe_wav(output_path).strip()
    try:
        from os import remove

        remove(output_path)
    except OSError:
        pass

    if not transcript:
        return "", {"error": "no_transcript"}

    return transcript, {}


def process_voice_turn(
    rico_app: RicoApp,
    context: AppContext,
    *,
    mode: str,
    timeout_ms: int,
    source: str,
) -> TurnResult:
    """Capture voice input and return a structured turn result."""

    metadata: dict[str, Any] = {"source": source, "mode": mode}
    if source == "web":
        transcript, transcript_meta = _transcribe_web(context, timeout_ms)
    else:
        transcript, transcript_meta = _transcribe_cli(context, timeout_ms)
    metadata.update(transcript_meta)

    if not transcript:
        logger.info(
            "orchestrator: gated transcript=%r mode=%s reason=%s",
            transcript,
            mode,
            "empty",
        )
        return _build_turn_result(
            transcript="",
            reply="",
            metadata=metadata,
            should_followup=False,
            followup_timeout_ms=0,
        )

    if mode in {"followup", "second_chance"}:
        should_reply, reason = _should_respond_with_reason(transcript)
    else:
        should_reply, reason = True, None

    if mode == "manual" and _is_acknowledgement(transcript):
        should_reply, reason = False, "ack"

    if mode in {"followup", "second_chance"} and not should_reply:
        metadata["gated"] = True
        metadata["gated_reason"] = reason
        logger.info(
            "orchestrator: gated transcript=%r mode=%s reason=%s",
            transcript,
            mode,
            reason,
        )
        should_followup = mode == "followup"
        timeout = SECOND_CHANCE_TIMEOUT_MS if should_followup else 0
        return _build_turn_result(
            transcript=transcript,
            reply="",
            metadata=metadata,
            should_followup=should_followup,
            followup_timeout_ms=timeout,
        )

    if mode == "manual" and not should_reply:
        metadata["gated"] = True
        metadata["gated_reason"] = reason
        logger.info(
            "orchestrator: gated transcript=%r mode=%s reason=%s",
            transcript,
            mode,
            reason,
        )
        return _build_turn_result(
            transcript=transcript,
            reply="",
            metadata=metadata,
            should_followup=False,
            followup_timeout_ms=0,
        )

    text_result = process_text_turn(rico_app, context, transcript, source)
    combined_metadata = dict(text_result.metadata or {})
    combined_metadata.update(metadata)
    combined_metadata.setdefault("source", source)
    combined_metadata["mode"] = mode

    should_followup = text_result.replied and not combined_metadata.get("exit")
    timeout = FOLLOWUP_TIMEOUT_MS if should_followup else 0

    return _build_turn_result(
        transcript=transcript,
        reply=text_result.reply,
        metadata=combined_metadata,
        should_followup=should_followup,
        followup_timeout_ms=timeout,
    )


__all__ = [
    "DEFAULT_MANUAL_TIMEOUT_MS",
    "FOLLOWUP_TIMEOUT_MS",
    "SECOND_CHANCE_TIMEOUT_MS",
    "TurnResult",
    "process_text_turn",
    "process_voice_turn",
    "should_respond",
]
