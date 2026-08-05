"""
Celery application configuration.

Workers process background jobs for:
- Export generation (Excel, PDF, DOCX, JSON, XML)
- Data import (CSV, Excel, JSON, XML)
- AI processing (embeddings, summaries, tagging)
- Email sending
- Scheduled database maintenance
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from src.core.config import settings

# ==============================================================================
# APPLICATION
# ==============================================================================


def create_celery_app() -> Celery:
    """Create and configure the Celery application."""
    app = Celery(
        "saints",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            "src.workers.tasks.exports",
            "src.workers.tasks.imports",
            "src.workers.tasks.ai",
            "src.workers.tasks.maintenance",
            "src.workers.tasks.notifications",
        ],
    )

    # Configuration
    app.conf.update(
        # Serialisation
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Europe/Warsaw",
        enable_utc=True,

        # Task routing
        task_routes={
            "src.workers.tasks.exports.*": {"queue": "exports"},
            "src.workers.tasks.imports.*": {"queue": "imports"},
            "src.workers.tasks.ai.*": {"queue": "ai"},
            "src.workers.tasks.maintenance.*": {"queue": "default"},
            "src.workers.tasks.notifications.*": {"queue": "default"},
        },

        # Queue definitions
        task_queues={
            "default": {"exchange": "default", "routing_key": "default"},
            "exports": {"exchange": "exports", "routing_key": "exports"},
            "imports": {"exchange": "imports", "routing_key": "imports"},
            "ai": {"exchange": "ai", "routing_key": "ai"},
        },

        # Reliability
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_max_retries=3,
        task_default_retry_delay=60,

        # Result TTL
        result_expires=86400 * 7,  # 7 days

        # Memory management
        worker_max_tasks_per_child=1000,

        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,

        # Beat schedule (periodic tasks)
        beat_schedule={
            # Clean up expired refresh tokens daily at 3 AM
            "cleanup-expired-tokens": {
                "task": "src.workers.tasks.maintenance.cleanup_expired_tokens",
                "schedule": crontab(hour=3, minute=0),
            },
            # Update person search vectors every night
            "refresh-search-vectors": {
                "task": "src.workers.tasks.maintenance.refresh_search_vectors",
                "schedule": crontab(hour=2, minute=0),
            },
            # Database statistics update
            "update-statistics": {
                "task": "src.workers.tasks.maintenance.update_statistics",
                "schedule": crontab(hour=4, minute=0),
            },
        },
    )

    return app


celery_app = create_celery_app()
