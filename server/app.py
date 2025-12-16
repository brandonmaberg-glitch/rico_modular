"""FastAPI server exposing the RICO web UI and chat endpoint."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config.settings import AppConfig
from rico.core.assistant import handle_text
from rico.voice.ptt_input import record_to_wav
from rico.voice.transcribe import transcribe_wav
from tts.speaker import Speaker


UI_DIR = Path(__file__).resolve().parent.parent / "rico_ui"
TTS_DIR = Path("./tmp/tts")
TTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RICO Web")
config = AppConfig.load()
tts_engine = Speaker(
    openai_api_key=config.openai_api_key,
    elevenlabs_api_key=config.elevenlabs_api_key,
    voice_id=config.elevenlabs_voice_id,
)


def _build_audio_file(text: str) -> str | None:
    """Generate TTS audio for the given text and return a relative URL."""

    synthesized = tts_engine.synthesize(text)
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

    result = handle_text(request.text)
    reply = result.get("reply") or ""
    metadata = result.get("metadata") or {}
    audio_url = _build_audio_file(reply)

    return ChatResponse(reply=reply, metadata=metadata, audio_url=audio_url)


@app.post("/api/voice_ptt", response_model=VoiceResponse)
async def voice_ptt() -> VoiceResponse:
    recording_path = f"./tmp/input_{uuid.uuid4().hex}.wav"

    output_path = record_to_wav(
        sample_rate=config.voice_sample_rate,
        max_seconds=config.voice_max_seconds,
        output_path=recording_path,
    )

    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Voice capture unavailable.")

    transcription = transcribe_wav(output_path).strip()
    result = handle_text(transcription)
    reply = result.get("reply") or ""
    metadata = result.get("metadata") or {}
    audio_url = _build_audio_file(reply)

    try:
        os.remove(recording_path)
    except OSError:
        pass

    return VoiceResponse(
        text=transcription,
        reply=reply,
        metadata=metadata,
        audio_url=audio_url,
    )


app.mount("/api/audio", StaticFiles(directory=TTS_DIR), name="audio")
app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
