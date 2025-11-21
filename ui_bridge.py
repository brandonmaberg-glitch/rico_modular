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
    _send_event({"type": "thinking", "intensity": max(0.0, min(intensity, 1.0))})


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
    _send_event({"type": "speaking", "active": bool(start)})


def send_listening(active: bool) -> None:
    _send_event({"type": "listening", "active": bool(active)})


__all__ = [
    "send_chart",
    "send_image",
    "send_listening",
    "send_provider",
    "send_reply",
    "send_skill",
    "send_speaking",
    "send_thinking",
    "send_transcription",
    "launch_ui",
    "start_ui_server",
    "stop_ui_server",
]
