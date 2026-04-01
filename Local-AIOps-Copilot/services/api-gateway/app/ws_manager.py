"""WebSocket connection manager for live events."""

from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections by session ID."""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self._connections.pop(session_id, None)

    async def send_to_session(self, session_id: str, data: dict):
        ws = self._connections.get(session_id)
        if ws:
            await ws.send_json(data)

    async def broadcast(self, data: dict):
        for ws in self._connections.values():
            await ws.send_json(data)

    @property
    def active_connections(self) -> int:
        return len(self._connections)
