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
        # Periodic maintenance is intentionally disabled until each task has a
        # real database implementation and an integration test. Scheduling a
        # no-op as "completed" would make operational monitoring misleading.
        beat_schedule={},
    )

    return app


celery_app = create_celery_app()
