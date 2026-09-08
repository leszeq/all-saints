"""Regression tests for the admin settings API contract."""

from __future__ import annotations

from src.main import app


def test_settings_endpoint_requires_bearer_auth() -> None:
    schema = app.openapi()

    assert schema["paths"]["/api/v1/settings"]["get"]["security"] == [{"HTTPBearer": []}]
    assert schema["paths"]["/api/v1/auth/me"]["patch"]["security"] == [{"HTTPBearer": []}]


def test_settings_contract_exposes_state_without_secret_fields() -> None:
    schemas = app.openapi()["components"]["schemas"]
    exposed_properties = {
        property_name
        for schema_name in (
            "ApplicationSettingsResponse",
            "AISettingsSchema",
            "StorageSettingsSchema",
            "SecuritySettingsSchema",
        )
        for property_name in schemas[schema_name]["properties"]
    }

    assert "openai_configured" in exposed_properties
    assert not any(
        marker in property_name
        for property_name in exposed_properties
        for marker in ("password", "secret", "api_key", "access_key")
    )
