"""FastAPI server exposing the RICO web UI and chat endpoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rico.core.assistant import handle_text


UI_DIR = Path(__file__).resolve().parent.parent / "rico_ui"

app = FastAPI(title="RICO Web")


class ChatRequest(BaseModel):
    text: str


class ChatResponse(BaseModel):
    reply: str
    metadata: dict | None = None


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    result = handle_text(request.text)
    reply = result.get("reply") or ""
    metadata = result.get("metadata") or {}

    return ChatResponse(reply=reply, metadata=metadata)


app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
