"""Celery background tasks for analysis orchestration."""
from __future__ import annotations

import asyncio
import structlog

from app.worker import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="tasks.run_analysis", max_retries=0)
def run_analysis_task(self, analysis_id: str) -> dict:
    """Celery entry-point — runs the full analysis pipeline for an analysis ID."""
    logger.info("analysis_task_started", analysis_id=analysis_id, task_id=self.request.id)
    try:
        # Import here to avoid circular imports at module load time
        from app.orchestration.pipeline import run_analysis_pipeline

        result = asyncio.get_event_loop().run_until_complete(
            run_analysis_pipeline(analysis_id)
        )
        logger.info("analysis_task_completed", analysis_id=analysis_id)
        return result
    except Exception as exc:
        logger.error("analysis_task_failed", analysis_id=analysis_id, error=str(exc))
        raise
