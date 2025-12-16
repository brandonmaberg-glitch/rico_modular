"""FastAPI server exposing the RICO web UI and chat endpoint."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rico.app import RicoApp
from rico.app_context import get_app_context


UI_DIR = Path(__file__).resolve().parent.parent / "rico_ui"
TTS_DIR = Path("./tmp/tts")
TTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RICO Web")
# Shared singleton context reused by both CLI and web layers.
context = get_app_context()
rico_app = RicoApp(context)


def _build_audio_file(text: str) -> str | None:
    """Generate TTS audio for the given text and return a relative URL."""

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
    reply: str
    metadata: dict | None = None
    audio_url: str | None = None


class VoiceResponse(BaseModel):
    text: str
    reply: str
    metadata: dict | None = None
    audio_url: str | None = None


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    result = rico_app.handle_text(request.text, source="web")
    reply = result.reply or ""
    metadata = result.metadata or {}
    audio_url = _build_audio_file(reply)

    return ChatResponse(reply=reply, metadata=metadata, audio_url=audio_url)


@app.post("/api/voice_ptt", response_model=VoiceResponse)
async def voice_ptt() -> VoiceResponse:
    result = rico_app.handle_voice_ptt(source="web")
    transcription = result.text or ""
    reply = result.reply or ""
    metadata = result.metadata or {}
    audio_url = _build_audio_file(reply)

    return VoiceResponse(
        text=transcription,
        reply=reply,
        metadata=metadata,
        audio_url=audio_url,
    )


app.mount("/api/audio", StaticFiles(directory=TTS_DIR), name="audio")
app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
