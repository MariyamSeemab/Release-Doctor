"""
WebSocket endpoint + Redis pub/sub relay.

Flow:
  1. Browser connects to /api/ws/analyses/{analysis_id}
  2. FastAPI registers the WS in _connections (in-process dict)
  3. A background task subscribes to Redis channel rd:analysis:{analysis_id}
  4. Redis messages (published by Celery worker) are relayed to all WS clients
  5. Clients can also subscribe with no running analysis — they wait for events

The in-process _connections dict is only used for the FastAPI-side relay.
The Celery worker MUST use events.publish_event() — never import _connections.
"""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Set

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = structlog.get_logger(__name__)
router = APIRouter()

# FastAPI-process-only: analysis_id → set of active WebSocket connections
_connections: Dict[str, Set[WebSocket]] = {}
# Track running subscriber tasks per analysis_id
_subscriber_tasks: Dict[str, asyncio.Task] = {}


async def broadcast(analysis_id: str, event: dict) -> None:
    """
    Broadcast to all WebSocket clients subscribed to this analysis.
    Called ONLY from within the FastAPI process (e.g. startup tasks, SSE routes).
    Celery workers MUST use app.events.publish_event() instead.
    """
    sockets = _connections.get(analysis_id, set())
    dead: Set[WebSocket] = set()
    for ws in sockets:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.add(ws)
    for ws in dead:
        sockets.discard(ws)


async def _redis_subscriber(analysis_id: str) -> None:
    """Background task: subscribe to Redis and relay events to WebSocket clients."""
    try:
        from app.config import settings

        # Try aioredis first, fall back to redis-py async
        try:
            import aioredis  # type: ignore[import]
            r = await aioredis.from_url(settings.redis_url)
            pubsub = r.pubsub()
            await pubsub.subscribe(f"rd:analysis:{analysis_id}")
            logger.info("redis_subscriber_started", analysis_id=analysis_id)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        await broadcast(analysis_id, event)
                        # Stop relaying after analysis is done
                        if event.get("event") in ("analysis_completed", "analysis_failed", "analysis_cancelled"):
                            break
                    except Exception as e:
                        logger.error("relay_decode_error", error=str(e))
            await pubsub.unsubscribe(f"rd:analysis:{analysis_id}")
            await r.close()
        except ImportError:
            # aioredis not available — use redis-py with asyncio wrapper
            import redis as redis_lib
            r = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe(f"rd:analysis:{analysis_id}")
            loop = asyncio.get_event_loop()
            while True:
                message = await loop.run_in_executor(None, pubsub.get_message, True, 0.1)
                if message and message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        await broadcast(analysis_id, event)
                        if event.get("event") in ("analysis_completed", "analysis_failed"):
                            break
                    except Exception:
                        pass
                await asyncio.sleep(0.05)
    except Exception as exc:
        logger.error("redis_subscriber_failed", analysis_id=analysis_id, error=str(exc))
        # If Redis is unavailable, fall back to polling: clients will use HTTP polling
    finally:
        _subscriber_tasks.pop(analysis_id, None)


@router.websocket("/analyses/{analysis_id}")
async def analysis_stream(ws: WebSocket, analysis_id: str) -> None:
    """WebSocket endpoint — clients subscribe to live analysis events."""
    await ws.accept()

    if analysis_id not in _connections:
        _connections[analysis_id] = set()
    _connections[analysis_id].add(ws)

    # Start a Redis subscriber task for this analysis if not already running
    if analysis_id not in _subscriber_tasks:
        task = asyncio.create_task(_redis_subscriber(analysis_id))
        _subscriber_tasks[analysis_id] = task

    try:
        # Keep connection alive; send pings every 25s
        while True:
            await asyncio.sleep(25)
            await ws.send_text(json.dumps({"event": "ping"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _connections.get(analysis_id, set()).discard(ws)
        # Clean up empty sets
        if not _connections.get(analysis_id):
            _connections.pop(analysis_id, None)
