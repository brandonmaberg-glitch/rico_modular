"""Unified application layer for both CLI and web entrypoints."""

from __future__ import annotations

import os
from dataclasses import dataclass

from rico.app_context import AppContext
from rico.commands import _handle_voice_command, _normalise_command, _should_exit
from rico.processing import handle_text_interaction
from rico.voice.vad_input import record_to_wav_vad
from rico.voice.transcribe import transcribe_wav


@dataclass
class RicoResponse:
    """Structured response returned by the unified handlers."""

    reply: str
    metadata: dict
    text: str | None = None
    wav_path: str | None = None


class RicoApp:
    """Single brain used by both CLI and Web interfaces."""

    def __init__(self, context: AppContext) -> None:
        self.context = context

    def handle_text(self, text: str, source: str) -> RicoResponse:
        """Main unified entrypoint for ALL text input (CLI + Web).

        Handles command parsing, shared memory routing, and skill execution using
        the exact same objects regardless of caller.
        """

        cleaned = text.strip()
        if not cleaned:
            return RicoResponse(
                reply="Please provide a command, Sir.", metadata={"source": source}
            )

        normalised = _normalise_command(cleaned)

        if _handle_voice_command(normalised, self.context.tts_engine):
            return RicoResponse(reply="", metadata={"source": source, "command": "voice"})

        if _should_exit(cleaned):
            return RicoResponse(
                reply="", metadata={"source": source, "command": "exit", "exit": True}
            )

        self.context.interaction_count += 1
        result = handle_text_interaction(
            user_text=cleaned,
            router=self.context.router,
            skill_registry=self.context.skill_registry,
            interaction_count=self.context.interaction_count,
        )

        reply = result.get("reply") or ""
        metadata = result.get("metadata") or {}
        metadata["source"] = source
        return RicoResponse(reply=reply, metadata=metadata)

    def handle_voice_ptt(self, source: str) -> RicoResponse:
        """Unified push-to-talk handler using the shared mic/STT pipeline."""

        if not self.context.config.voice_enabled:
            return RicoResponse(
                reply="", metadata={"source": source, "error": "voice_disabled"}
            )

        self.context.logger.info("Using VAD recorder.")
        output_path = record_to_wav_vad(
            sample_rate=self.context.config.vad_sample_rate,
            max_seconds=self.context.config.vad_max_seconds,
            silence_ms=self.context.config.vad_silence_ms,
            aggressiveness=self.context.config.vad_aggressiveness,
            pre_roll_ms=self.context.config.vad_pre_roll_ms,
            min_voiced_ms=self.context.config.vad_min_voiced_ms,
        )
        if not output_path:
            return RicoResponse(
                reply="",
                metadata={"source": source, "error": "no_speech"},
                wav_path=None,
            )

        transcript = transcribe_wav(output_path).strip()
        if not transcript:
            try:
                os.remove(output_path)
            except OSError:
                pass
            return RicoResponse(
                reply="",
                metadata={"source": source, "error": "no_transcript"},
                wav_path=output_path,
            )

        response = self.handle_text(transcript, source=source)
        response.text = transcript
        response.wav_path = output_path

        try:
            os.remove(output_path)
        except OSError:
            pass

        return response


__all__ = ["RicoApp", "RicoResponse"]
