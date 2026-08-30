"""Regression tests for environment-specific security settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.config import Environment, Settings


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_SECRET_KEY": "development-secret",
        "JWT_SECRET_KEY": "development-jwt-secret",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": 5432,
        "POSTGRES_PASSWORD": "development-database-password",
        "DATABASE_URL": None,
        "DATABASE_URL_SYNC": None,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_development_allows_local_insecure_configuration() -> None:
    settings = _settings(APP_ENV=Environment.DEVELOPMENT, SECURE_COOKIES=False)

    assert settings.is_development
    assert not settings.SECURE_COOKIES


def test_production_accepts_independent_strong_secrets() -> None:
    settings = _settings(
        APP_ENV=Environment.PRODUCTION,
        APP_SECRET_KEY="a" * 64,
        JWT_SECRET_KEY="b" * 64,
        SECURE_COOKIES=True,
    )

    assert settings.is_production
    assert settings.docs_url is None


def test_database_url_components_are_percent_encoded() -> None:
    settings = _settings(
        POSTGRES_USER="saints+editor",
        POSTGRES_PASSWORD="p@ss:/?#[]",
        POSTGRES_DB="all saints",
    )

    assert settings.DATABASE_URL == (
        "postgresql+asyncpg://saints%2Beditor:p%40ss%3A%2F%3F%23%5B%5D"
        "@localhost:5432/all%20saints"
    )
    assert settings.DATABASE_URL_SYNC == (
        "postgresql://saints%2Beditor:p%40ss%3A%2F%3F%23%5B%5D"
        "@localhost:5432/all%20saints"
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"APP_SECRET_KEY": "REPLACE_WITH_A_RANDOM_SECRET"}, "APP_SECRET_KEY"),
        ({"JWT_SECRET_KEY": "too-short"}, "JWT_SECRET_KEY"),
        ({"JWT_SECRET_KEY": "a" * 64}, "must be different"),
        ({"POSTGRES_PASSWORD": "REPLACE_WITH_A_PASSWORD"}, "POSTGRES_PASSWORD"),
        ({"SECURE_COOKIES": False}, "SECURE_COOKIES"),
        ({"ALLOWED_HOSTS": ["*"]}, "ALLOWED_HOSTS"),
        ({"CORS_ORIGINS": ["*"]}, "CORS_ORIGINS"),
    ],
)
def test_production_rejects_unsafe_security_settings(
    overrides: dict[str, object], message: str
) -> None:
    production_values: dict[str, object] = {
        "APP_ENV": Environment.PRODUCTION,
        "APP_SECRET_KEY": "a" * 64,
        "JWT_SECRET_KEY": "b" * 64,
        "SECURE_COOKIES": True,
    }
    production_values.update(overrides)

    with pytest.raises(ValidationError, match=message):
        _settings(**production_values)
