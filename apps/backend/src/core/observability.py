"""Optional error and performance monitoring integrations."""

from __future__ import annotations

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from src.core.config import Settings


def configure_error_monitoring(settings: Settings) -> bool:
    """Initialize Sentry when a DSN is configured and report whether it is active."""
    if not settings.SENTRY_DSN:
        return False

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV.value,
        release=f"all-saints-backend@{settings.APP_VERSION}",
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )
    logger.info(
        "Sentry error monitoring initialised",
        environment=settings.APP_ENV.value,
        tracing=settings.SENTRY_TRACES_SAMPLE_RATE > 0,
    )
    return True
