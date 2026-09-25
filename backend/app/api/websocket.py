"""WebSocket / Server-Sent Events for live agent streaming."""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# In-memory pub/sub hub: analysis_id -> set of connected websockets
_connections: Dict[str, Set[WebSocket]] = {}


async def broadcast(analysis_id: str, event: dict) -> None:
    """Broadcast an event to all subscribers of an analysis."""
    sockets = _connections.get(analysis_id, set())
    dead: Set[WebSocket] = set()
    for ws in sockets:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.add(ws)
    for ws in dead:
        sockets.discard(ws)


@router.websocket("/analyses/{analysis_id}")
async def analysis_stream(ws: WebSocket, analysis_id: str) -> None:
    """WebSocket endpoint — clients subscribe to live analysis events."""
    await ws.accept()
    if analysis_id not in _connections:
        _connections[analysis_id] = set()
    _connections[analysis_id].add(ws)
    try:
        while True:
            # Keep the connection alive; clients only listen
            await asyncio.sleep(30)
            await ws.send_text(json.dumps({"event": "ping"}))
    except WebSocketDisconnect:
        _connections[analysis_id].discard(ws)
    except Exception:
        _connections[analysis_id].discard(ws)
