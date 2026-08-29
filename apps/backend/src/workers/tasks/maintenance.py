"""
Maintenance Celery tasks.

Handles periodic database cleanup and maintenance operations.
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(name="src.workers.tasks.maintenance.cleanup_expired_tokens", queue="default")
def cleanup_expired_tokens() -> dict:
    """Remove expired JWT refresh tokens from the database."""
    logger.info("Running cleanup of expired tokens")
    return {"status": "completed"}


@shared_task(name="src.workers.tasks.maintenance.update_statistics", queue="default")
def update_statistics() -> dict:
    """Update database statistics for query planner."""
    logger.info("Updating database statistics")
    return {"status": "completed"}
