"""Lightweight WebSocket broadcast server for the RICO UI."""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any, Dict, Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol


logger = logging.getLogger(__name__)


class UIBroadcastServer:
    """Async WebSocket server that broadcasts events to all clients."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._clients: Set[WebSocketServerProtocol] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = threading.Event()

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        logger.info("UI connected: %s", websocket.remote_address)
        self._clients.add(websocket)
        try:
            async for _ in websocket:
                # The UI currently only listens; future commands may be handled here.
                continue
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("WebSocket connection error: %s", exc)
        finally:
            self._clients.discard(websocket)
            logger.info("UI disconnected: %s", websocket.remote_address)

    async def _serve(self) -> None:
        async with websockets.serve(self._handler, self.host, self.port, ping_interval=20):
            self._started.set()
            await asyncio.Future()  # Run forever until the loop is stopped.

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("WebSocket server terminated unexpectedly: %s", exc)
        finally:
            if self._loop.is_running():
                self._loop.stop()
            self._loop.close()

    def start(self) -> None:
        """Start the WebSocket server in a background thread."""

        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._started.wait(timeout=3.0)

    def stop(self) -> None:
        """Stop the running server and close the loop."""

        if not self._loop:
            return
        for client in list(self._clients):
            try:
                self._loop.call_soon_threadsafe(lambda ws=client: asyncio.create_task(ws.close()))
            except Exception:  # pragma: no cover - best effort
                continue
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)

    async def _broadcast(self, message: str) -> None:
        if not self._clients:
            return
        await asyncio.gather(
            *(client.send(message) for client in list(self._clients)),
            return_exceptions=True,
        )

    def send(self, payload: Dict[str, Any]) -> None:
        """Serialize and broadcast a payload to all connected clients."""

        if not self._loop:
            return
        try:
            message = json.dumps(payload)
        except TypeError as exc:
            logger.error("Failed to serialize payload for UI: %s", exc)
            return

        asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)


__all__ = ["UIBroadcastServer"]
