"""
Maintenance Celery tasks.

Handles periodic database cleanup and maintenance operations.
"""

from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(name="src.workers.tasks.maintenance.cleanup_expired_tokens", queue="default")
def cleanup_expired_tokens() -> dict[str, str]:
    """Report the task as disabled until persistent cleanup is implemented."""
    logger.warning("Expired-token cleanup is disabled: implementation pending")
    return {"status": "disabled", "reason": "not_implemented"}


@shared_task(name="src.workers.tasks.maintenance.update_statistics", queue="default")
def update_statistics() -> dict[str, str]:
    """Report the task as disabled until database ANALYZE is implemented."""
    logger.warning("Statistics maintenance is disabled: implementation pending")
    return {"status": "disabled", "reason": "not_implemented"}
