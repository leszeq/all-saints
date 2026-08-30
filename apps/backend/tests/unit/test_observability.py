"""Tests for optional monitoring and production log serialization."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
import sentry_sdk
from pydantic import ValidationError

import src.core.logging as logging_module
from src.core.config import Environment, Settings
from src.core.observability import configure_error_monitoring


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_SECRET_KEY": "development-secret",
        "JWT_SECRET_KEY": "development-jwt-secret",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PASSWORD": "development-database-password",
        "DATABASE_URL": None,
        "DATABASE_URL_SYNC": None,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_sentry_remains_disabled_without_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    init = Mock()
    monkeypatch.setattr(sentry_sdk, "init", init)

    assert not configure_error_monitoring(_settings(SENTRY_DSN=""))
    init.assert_not_called()


def test_sentry_uses_safe_environment_and_sampling_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init = Mock()
    monkeypatch.setattr(sentry_sdk, "init", init)

    enabled = configure_error_monitoring(
        _settings(
            APP_ENV=Environment.STAGING,
            APP_VERSION="2.3.4",
            SENTRY_DSN="https://public@example.invalid/1",
            SENTRY_TRACES_SAMPLE_RATE=0.25,
        )
    )

    assert enabled
    options = init.call_args.kwargs
    assert options["environment"] == "staging"
    assert options["release"] == "all-saints-backend@2.3.4"
    assert options["traces_sample_rate"] == 0.25
    assert options["send_default_pii"] is False
    assert len(options["integrations"]) == 2


def test_sentry_sampling_rate_is_bounded() -> None:
    with pytest.raises(ValidationError, match="SENTRY_TRACES_SAMPLE_RATE"):
        _settings(SENTRY_TRACES_SAMPLE_RATE=1.1)


def test_production_logging_uses_loguru_json_serializer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loguru = Mock()
    monkeypatch.setattr(logging_module, "logger", loguru)

    logging_module._add_stdout_sink(log_level="INFO", json_logs=True)

    options: dict[str, Any] = loguru.add.call_args.kwargs
    assert options["serialize"] is True
    assert options["colorize"] is False
    assert options["diagnose"] is False
    assert "format" not in options
