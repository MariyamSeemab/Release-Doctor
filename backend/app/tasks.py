"""Celery background tasks for analysis orchestration.

Dispatch strategy
-----------------
Call `dispatch_analysis(analysis_id)` from API handlers — never call
`run_analysis_task.delay()` directly.  The dispatcher will:

1. Use Celery (Redis broker) when `USE_INLINE_TASKS=false` (default) AND
   the broker is reachable.
2. Fall back to an asyncio background task running inside the FastAPI process
   when Celery is unavailable or `USE_INLINE_TASKS=true`.

This lets the app work on free-tier Railway/Render deployments that have
a single dyno and no Redis, while still using the full Celery pipeline when
Redis is available.
"""
from __future__ import annotations

import asyncio
import structlog

from app.worker import celery_app
from app.config import settings

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="tasks.run_analysis", max_retries=0)
def run_analysis_task(self, analysis_id: str) -> dict:
    """Celery entry-point — runs the full analysis pipeline for an analysis ID."""
    logger.info("analysis_task_started", analysis_id=analysis_id, task_id=self.request.id)
    try:
        from app.orchestration.pipeline import run_analysis_pipeline
        # asyncio.run() creates a fresh event loop — correct for Celery worker threads
        result = asyncio.run(run_analysis_pipeline(analysis_id))
        logger.info("analysis_task_completed", analysis_id=analysis_id)
        return result
    except Exception as exc:
        logger.error("analysis_task_failed", analysis_id=analysis_id, error=str(exc))
        raise


async def _run_inline(analysis_id: str) -> None:
    """Run the pipeline directly in the FastAPI event loop (no Celery required)."""
    try:
        from app.orchestration.pipeline import run_analysis_pipeline
        await run_analysis_pipeline(analysis_id)
    except Exception as exc:
        logger.error("inline_task_failed", analysis_id=analysis_id, error=str(exc))


def _broker_is_reachable() -> bool:
    """Quick TCP probe to see if the Celery broker (Redis) is reachable."""
    try:
        import redis as redis_lib
        client = redis_lib.Redis.from_url(settings.celery_broker_url, socket_connect_timeout=2)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


def dispatch_analysis(analysis_id: str) -> None:
    """
    Dispatch an analysis task using the best available strategy:
    - Celery (via Redis) when available and USE_INLINE_TASKS is false
    - asyncio background task otherwise (in-process, no Redis needed)
    """
    use_inline = settings.use_inline_tasks

    if not use_inline:
        # Try Celery first; fall back on any connection error
        try:
            if _broker_is_reachable():
                run_analysis_task.delay(analysis_id)
                logger.info("analysis_dispatched_celery", analysis_id=analysis_id)
                return
            else:
                logger.warning(
                    "celery_broker_unreachable_falling_back_to_inline",
                    analysis_id=analysis_id,
                )
        except Exception as exc:
            logger.warning(
                "celery_dispatch_failed_falling_back_to_inline",
                analysis_id=analysis_id,
                error=str(exc),
            )

    # Inline path: schedule as a background coroutine on the running event loop
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_run_inline(analysis_id))
        logger.info("analysis_dispatched_inline", analysis_id=analysis_id)
    except RuntimeError:
        # No running event loop — shouldn't happen in FastAPI context, but handle gracefully
        logger.error(
            "no_event_loop_for_inline_task",
            analysis_id=analysis_id,
        )
        asyncio.run(_run_inline(analysis_id))
