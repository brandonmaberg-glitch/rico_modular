"""Helper functions to broadcast runtime events to the Jarvis-style UI."""
from __future__ import annotations

import logging
import pathlib
import webbrowser
from typing import Any, Dict, Optional

from websocket_server import UIBroadcastServer


logger = logging.getLogger(__name__)

_server: Optional[UIBroadcastServer] = None


def start_ui_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the background WebSocket server if it is not already running."""

    global _server
    if _server is None:
        _server = UIBroadcastServer(host=host, port=port)
    _server.start()


def stop_ui_server() -> None:
    """Stop the WebSocket server if it is running."""

    if _server:
        _server.stop()


def _send_event(payload: Dict[str, Any]) -> None:
    if _server is None:
        return
    _server.send(payload)


def launch_ui() -> None:
    """Open the local UI in the default browser."""

    ui_path = pathlib.Path(__file__).parent / "rico_ui" / "index.html"
    if not ui_path.exists():
        logger.warning("UI assets not found at %s", ui_path)
        return
    try:
        webbrowser.open_new_tab(ui_path.as_uri())
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to open UI in browser: %s", exc)


def send_transcription(text: str) -> None:
    _send_event({"type": "transcription", "text": text})


def send_reply(text: str) -> None:
    _send_event({"type": "speech", "text": text})


def send_thinking(intensity: float = 0.5) -> None:
    value = max(0.0, min(intensity, 1.0))
    _send_event({"type": "thinking", "intensity": value})
    send_state("thinking", value > 0)


def send_image(url: str, caption: str | None = None) -> None:
    payload: Dict[str, Any] = {"type": "image", "url": url}
    if caption:
        payload["caption"] = caption
    _send_event(payload)


def send_chart(data: Dict[str, Any], title: str | None = None) -> None:
    payload: Dict[str, Any] = {"type": "chart", "data": data}
    if title:
        payload["title"] = title
    _send_event(payload)


def send_skill(skill_name: str) -> None:
    _send_event({"type": "skill", "skill": skill_name})


def send_provider(provider: str) -> None:
    _send_event({"type": "provider", "provider": provider})


def send_speaking(start: bool) -> None:
    active = bool(start)
    _send_event({"type": "speaking", "active": active})
    send_state("speaking", active)


def send_speaking_start() -> None:
    _send_event({"type": "speaking_start"})
    send_state("speaking", True)


def send_speaking_end() -> None:
    _send_event({"type": "speaking_end"})
    send_state("speaking", False)


def send_audio_level(level: float) -> None:
    _send_event({"type": "audio_level", "value": max(0.0, min(level, 1.0))})


def send_listening(active: bool) -> None:
    state = bool(active)
    _send_event({"type": "listening", "active": state})
    send_state("listening", state)


def send_state(state: str, active: bool | None = None) -> None:
    payload: Dict[str, Any] = {"type": "state", "state": state}
    if active is not None:
        payload["active"] = bool(active)
    _send_event(payload)


def send_image_results(images: list[str]) -> None:
    _send_event({"type": "image_results", "images": images})


def send_web_preview(title: str, snippet: str, url: str, image: str | None = None) -> None:
    payload: Dict[str, Any] = {
        "type": "web_preview",
        "title": title,
        "snippet": snippet,
        "url": url,
    }
    if image:
        payload["image"] = image
    _send_event(payload)


__all__ = [
    "send_chart",
    "send_audio_level",
    "send_image_results",
    "send_image",
    "send_listening",
    "send_provider",
    "send_reply",
    "send_skill",
    "send_speaking_end",
    "send_speaking_start",
    "send_speaking",
    "send_state",
    "send_thinking",
    "send_transcription",
    "send_web_preview",
    "launch_ui",
    "start_ui_server",
    "stop_ui_server",
]
