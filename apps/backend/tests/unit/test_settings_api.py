"""Regression tests for the admin settings API contract."""

from __future__ import annotations

from src.main import app


def test_settings_endpoint_requires_bearer_auth() -> None:
    schema = app.openapi()

    assert schema["paths"]["/api/v1/settings"]["get"]["security"] == [{"HTTPBearer": []}]
    assert schema["paths"]["/api/v1/auth/me"]["patch"]["security"] == [{"HTTPBearer": []}]
