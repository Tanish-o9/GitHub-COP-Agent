"""
Real-Time WebSocket Connection Manager
Broadcasts live agent progress events (run.started, agent.completed, approval.required, run.completed) to connected UI clients.
"""
import asyncio
from typing import Dict, List, Set, Any
from fastapi import WebSocket


class WebSocketConnectionManager:
    """
    Manages active WebSocket connections per run ID.
    """

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket):
        """Accept connection and register under run_id."""
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = set()
        self.active_connections[run_id].add(websocket)

    def disconnect(self, run_id: str, websocket: WebSocket):
        """Remove disconnected client."""
        if run_id in self.active_connections:
            self.active_connections[run_id].discard(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast_run_event(self, run_id: str, event_type: str, data: Dict[str, Any]):
        """Broadcast progress event to all connected listeners for a run."""
        payload = {
            "event": event_type,
            "run_id": run_id,
            "data": data
        }
        if run_id in self.active_connections:
            dead_sockets = set()
            for ws in self.active_connections[run_id]:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead_sockets.add(ws)
            for ws in dead_sockets:
                self.active_connections[run_id].discard(ws)


ws_manager = WebSocketConnectionManager()
