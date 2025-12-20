"""FastAPI server exposing the RICO web UI and chat endpoint."""

from __future__ import annotations

import uuid
from pathlib import Path

import logging

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rico.app import RicoApp
from rico.app_context import get_app_context
from rico.conversation.orchestrator import (
    DEFAULT_MANUAL_TIMEOUT_MS,
    process_text_turn,
    process_voice_turn,
)
from ui_bridge import is_speaking


UI_DIR = Path(__file__).resolve().parent.parent / "rico_ui"
TTS_DIR = Path("./tmp/tts")
TTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RICO Web")
# Shared singleton context reused by both CLI and web layers.
context = get_app_context()
rico_app = RicoApp(context)
logger = logging.getLogger("RICO")


def _build_audio_file(text: str) -> str | None:
    """Generate TTS audio for the given text and return a relative URL."""

    if not text.strip():
        return None

    synthesized = context.tts_engine.synthesize(text)
    if not synthesized:
        return None

    audio_bytes, suffix = synthesized
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex
    audio_path = TTS_DIR / f"{file_id}{suffix}"
    audio_path.write_bytes(audio_bytes)

    return f"/api/audio/{audio_path.name}"


class ChatRequest(BaseModel):
    text: str


class ChatResponse(BaseModel):
    text: str
    reply: str
    replied: bool
    should_followup: bool
    followup_timeout_ms: int
    metadata: dict | None = None
    audio_url: str | None = None


class VoiceRequest(BaseModel):
    mode: str = "manual"
    timeout_ms: int = DEFAULT_MANUAL_TIMEOUT_MS


class VoiceResponse(BaseModel):
    text: str
    reply: str
    replied: bool
    should_followup: bool
    followup_timeout_ms: int
    metadata: dict | None = None
    audio_url: str | None = None


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    turn = process_text_turn(rico_app, context, request.text, source="web")
    reply = turn.reply or ""
    metadata = turn.metadata or {}
    audio_url = _build_audio_file(reply)

    return ChatResponse(
        text=turn.transcript,
        reply=reply,
        replied=turn.replied,
        should_followup=turn.should_followup,
        followup_timeout_ms=turn.followup_timeout_ms,
        metadata=metadata,
        audio_url=audio_url,
    )


@app.post("/api/voice_ptt", response_model=VoiceResponse)
async def voice_ptt(request: VoiceRequest = Body(default_factory=VoiceRequest)) -> VoiceResponse:
    logger.info("voice_ptt: ENTER endpoint")
    if is_speaking():
        raise HTTPException(
            status_code=409,
            detail="RICO is speaking right now. Please wait for playback to finish.",
        )
    try:
        logger.info(
            "voice_ptt: starting audio recording (VAD) mode=%s timeout_ms=%d",
            request.mode,
            request.timeout_ms,
        )
        turn = process_voice_turn(
            rico_app,
            context,
            mode=request.mode,
            timeout_ms=request.timeout_ms,
            source="web",
        )
        transcription = turn.transcript or ""
        logger.info("voice_ptt: transcription result=%r", transcription)
        logger.info("voice_ptt: sending text to RICO handler")
        reply = turn.reply or ""
        metadata = turn.metadata or {}

        logger.info(
            "voice_ptt: reply_len=%d reply_preview=%r",
            len(reply or ""),
            (reply[:60] if reply else ""),
        )

        error = metadata.get("error")
        if error == "no_speech":
            return JSONResponse(
                status_code=422,
                content={
                    "error": "no_speech",
                    "message": "I didn't catch that. Try again.",
                },
            )
        if error == "no_transcript":
            return JSONResponse(
                status_code=422,
                content={
                    "error": "no_transcript",
                    "message": "I couldn't transcribe that. Try again.",
                },
            )

        audio_url = _build_audio_file(reply)

        logger.info("voice_ptt: EXIT endpoint with success response")
        return VoiceResponse(
            text=transcription,
            reply=reply,
            replied=turn.replied,
            should_followup=turn.should_followup,
            followup_timeout_ms=turn.followup_timeout_ms,
            metadata=metadata,
            audio_url=audio_url,
        )
    except Exception as exc:
        logger.exception("voice_ptt: EXCEPTION occurred")
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An internal error occurred.",
            },
        )


app.mount("/api/audio", StaticFiles(directory=TTS_DIR), name="audio")
app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
