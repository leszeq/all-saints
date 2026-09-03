"""Shared HTTP error contract and FastAPI exception handlers."""

from __future__ import annotations

from http import HTTPStatus
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

type JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


_ERROR_CODES = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
}


def _request_id(request: Request) -> str | None:
    """Return the correlation ID assigned by middleware, when available."""
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


def _error_code(status_code: int) -> str:
    """Map an HTTP status to a stable, machine-readable error code."""
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return "INTERNAL_SERVER_ERROR"
    return _ERROR_CODES.get(status_code, "HTTP_ERROR")


def _default_message(status_code: int) -> str:
    """Provide a safe fallback when an exception has no textual detail."""
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Żądanie nie mogło zostać obsłużone"


def _as_json_value(value: object | None) -> JsonValue:
    """Convert framework exception details into JSON-compatible values."""
    return cast(JsonValue, jsonable_encoder(value))


def _http_message(detail: object, status_code: int) -> str:
    """Extract a user-facing message without changing the legacy detail value."""
    if isinstance(detail, str) and detail:
        return detail
    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str) and message:
            return message
    return _default_message(status_code)


def _http_details(detail: object) -> JsonValue:
    """Expose optional structured context in the canonical details field."""
    if not isinstance(detail, dict):
        return None
    structured_details = detail.get("details", detail.get("errors"))
    return _as_json_value(structured_details)


def error_content(
    *,
    code: str,
    message: str,
    detail: object | None,
    details: object | None,
    request_id: str | None,
) -> dict[str, JsonValue]:
    """Build the API-wide envelope while retaining FastAPI's legacy detail field."""
    return {
        "error": code,
        "message": message,
        "detail": _as_json_value(detail),
        "details": _as_json_value(details),
        "request_id": request_id,
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Register safe, correlated and backward-compatible exception handlers."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_content(
                code=_error_code(exc.status_code),
                message=_http_message(exc.detail, exc.status_code),
                detail=exc.detail,
                details=_http_details(exc.detail),
                request_id=_request_id(request),
            ),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors: list[dict[str, str]] = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": str(error["msg"]),
                    "type": str(error["type"]),
                }
            )
        message = "Dane wejściowe zawierają błędy walidacji"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_content(
                code="VALIDATION_ERROR",
                message=message,
                detail=errors,
                details=errors,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        logger.warning("Database integrity error: {error}", error=exc)
        message = "Naruszenie unikalności danych – rekord już istnieje"
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_content(
                code="CONFLICT",
                message=message,
                detail=message,
                details=None,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception on {method} {url}",
            method=request.method,
            url=request.url,
        )
        message = "Wystąpił nieoczekiwany błąd serwera"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_content(
                code="INTERNAL_SERVER_ERROR",
                message=message,
                detail=message,
                details=None,
                request_id=_request_id(request),
            ),
        )
