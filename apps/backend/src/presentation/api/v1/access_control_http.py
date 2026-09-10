"""Shared HTTP error mapping for user and role administration."""

from typing import NoReturn

from fastapi import HTTPException, status

from src.application.services.access_control_errors import (
    AccessControlNotFoundError,
    AccessControlValidationError,
)


def raise_access_error(exc: ValueError) -> NoReturn:
    """Map access-control failures to the stable HTTP status contract."""
    if isinstance(exc, AccessControlNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, AccessControlValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
