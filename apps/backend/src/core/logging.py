"""
Logging configuration using Loguru.

Provides structured JSON logging in production and human-readable
colourized output in development.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Message


# ==============================================================================
# INTERCEPT HANDLER – routes stdlib logging to Loguru
# ==============================================================================


class InterceptHandler(logging.Handler):
    """
    Intercepts standard library logging records and forwards them to Loguru.

    This ensures that all third-party libraries (SQLAlchemy, Uvicorn, etc.)
    use the same structured logging pipeline.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Forward a stdlib log record to Loguru."""
        # Determine the corresponding Loguru level
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Walk up the call stack to find the actual caller
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ==============================================================================
# SETUP
# ==============================================================================


def setup_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_logs: If True, output structured JSON (for production log aggregation).
    """
    # Remove default Loguru handler
    logger.remove()

    # Choose format based on environment
    if json_logs:
        fmt = (
            '{{"time":"{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level":"{level}", '
            '"logger":"{name}", '
            '"message":"{message}", '
            '"function":"{function}", '
            '"line":{line}}}'
        )
    else:
        fmt = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Add stdout sink
    logger.add(
        sys.stdout,
        format=fmt,
        level=log_level,
        colorize=not json_logs,
        backtrace=True,
        diagnose=not json_logs,
        enqueue=True,  # thread-safe
    )

    # Intercept all stdlib loggers
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Quiet noisy libraries
    for noisy_logger in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "celery",
        "kombu",
        "redis",
        "asyncio",
    ):
        logging.getLogger(noisy_logger).handlers = [InterceptHandler()]
        logging.getLogger(noisy_logger).propagate = False

    logger.info(
        "Logging initialised",
        level=log_level,
        json=json_logs,
    )
