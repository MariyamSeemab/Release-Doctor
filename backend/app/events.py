"""
Event bus for analysis streaming — uses Redis pub/sub so events
published by Celery workers are received by the FastAPI WebSocket server.

Architecture:
  Celery worker  →  publish(channel, event)  →  Redis pub/sub
  FastAPI server ←  subscribe(channel)       ←  Redis pub/sub
  FastAPI server →  ws.send_text(event)      →  Browser client
"""
from __future__ import annotations

import json
from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)


def _get_redis_client():
    """Get a synchronous Redis client for publishing from Celery workers."""
    try:
        import redis as redis_lib
        from app.config import settings
        return redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
    except ImportError:
        return None


def publish_event(channel: str, event: Dict[str, Any]) -> None:
    """Publish an event to Redis — called from Celery worker (sync context)."""
    client = _get_redis_client()
    if client is None:
        logger.warning("redis_unavailable_publish_skipped", channel=channel)
        return
    try:
        client.publish(f"rd:analysis:{channel}", json.dumps(event))
    except Exception as exc:
        logger.error("redis_publish_failed", channel=channel, error=str(exc))


async def publish_event_async(channel: str, event: Dict[str, Any]) -> None:
    """Publish an event from async context (FastAPI)."""
    try:
        import aioredis  # type: ignore[import]
        from app.config import settings
        r = await aioredis.from_url(settings.redis_url)
        await r.publish(f"rd:analysis:{channel}", json.dumps(event))
        await r.close()
    except ImportError:
        # Fall back to sync publish via threadpool
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, publish_event, channel, event)
    except Exception as exc:
        logger.error("async_publish_failed", channel=channel, error=str(exc))
