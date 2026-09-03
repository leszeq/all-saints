"""Contract tests for the API-wide error response envelope."""

from typing import Annotated

import pytest
from fastapi import FastAPI, HTTPException, Path, Request
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from src.main import _setup_exception_handlers


class ValidationPayload(BaseModel):
    """Minimal request model used to exercise validation errors."""

    amount: int = Field(ge=1)


def _create_test_app() -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = "request-test-123"
        return await call_next(request)

    @app.get("/protected")
    async def protected() -> None:
        raise HTTPException(
            status_code=401,
            detail="Wymagane uwierzytelnienie",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.get("/conflicts/{item_id}")
    async def conflict(item_id: Annotated[int, Path(ge=1)]) -> None:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Rekord został zmieniony przez innego użytkownika",
                "expected_version": item_id,
            },
        )

    @app.post("/validated")
    async def validated(payload: ValidationPayload) -> ValidationPayload:
        return payload

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("sensitive internal details")

    _setup_exception_handlers(app)
    return app


@pytest.fixture
async def error_client():
    test_app = _create_test_app()
    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_http_exception_uses_compatible_error_envelope(error_client: AsyncClient):
    response = await error_client.get("/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "error": "UNAUTHORIZED",
        "message": "Wymagane uwierzytelnienie",
        "detail": "Wymagane uwierzytelnienie",
        "details": None,
        "request_id": "request-test-123",
    }


@pytest.mark.asyncio
async def test_structured_http_detail_is_preserved(error_client: AsyncClient):
    response = await error_client.get("/conflicts/7")

    assert response.status_code == 409
    assert response.json() == {
        "error": "CONFLICT",
        "message": "Rekord został zmieniony przez innego użytkownika",
        "detail": {
            "message": "Rekord został zmieniony przez innego użytkownika",
            "expected_version": 7,
        },
        "details": None,
        "request_id": "request-test-123",
    }


@pytest.mark.asyncio
async def test_validation_error_uses_the_same_envelope(error_client: AsyncClient):
    response = await error_client.post("/validated", json={"amount": 0})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"] == "VALIDATION_ERROR"
    assert payload["message"] == "Dane wejściowe zawierają błędy walidacji"
    assert payload["detail"] == payload["details"]
    assert payload["details"] == [
        {
            "field": "body.amount",
            "message": "Input should be greater than or equal to 1",
            "type": "greater_than_equal",
        }
    ]
    assert payload["request_id"] == "request-test-123"


@pytest.mark.asyncio
async def test_unhandled_error_does_not_leak_internal_details(error_client: AsyncClient):
    response = await error_client.get("/boom")

    assert response.status_code == 500
    payload = response.json()
    assert payload == {
        "error": "INTERNAL_SERVER_ERROR",
        "message": "Wystąpił nieoczekiwany błąd serwera",
        "detail": "Wystąpił nieoczekiwany błąd serwera",
        "details": None,
        "request_id": "request-test-123",
    }
    assert "sensitive internal details" not in response.text
