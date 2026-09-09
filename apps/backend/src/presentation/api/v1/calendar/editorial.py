"""Protected editorial API for liturgical observances and assignments."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.calendar_service import (
    CalendarNotFoundError,
    CalendarService,
    FeastConflictError,
    FeastNotFoundError,
    ObservanceConflictError,
    ObservanceNotFoundError,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.calendar.schemas import (
    FeastEntryCreateSchema,
    FeastEntrySchema,
    FeastEntryUpdateSchema,
    LiturgicalObservanceCreateSchema,
    LiturgicalObservanceSchema,
    LiturgicalObservanceUpdateSchema,
)

router = APIRouter()


@router.get(
    "/persons/{person_id}/entries",
    response_model=list[FeastEntrySchema],
    summary="List calendar assignments for a person",
    description="Protected editorial lookup used by the admin person form.",
)
async def list_person_entries(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("calendar", "read")),
) -> list[FeastEntrySchema]:
    service = CalendarService(db)
    try:
        entries = await service.list_person_entries(person_id)
    except FeastNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [FeastEntrySchema.model_validate(entry) for entry in entries]


@router.post(
    "/observances",
    response_model=LiturgicalObservanceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a non-person liturgical observance",
)
async def create_observance(
    data: LiturgicalObservanceCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("calendar", "create")),
) -> LiturgicalObservanceSchema:
    service = CalendarService(db)
    try:
        observance = await service.create_observance(data)
    except ObservanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return LiturgicalObservanceSchema.model_validate(observance)


@router.patch(
    "/observances/{observance_id}",
    response_model=LiturgicalObservanceSchema,
    summary="Update a non-person liturgical observance",
)
async def update_observance(
    observance_id: uuid.UUID,
    data: LiturgicalObservanceUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("calendar", "update")),
) -> LiturgicalObservanceSchema:
    service = CalendarService(db)
    try:
        observance = await service.update_observance(observance_id, data)
    except ObservanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ObservanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return LiturgicalObservanceSchema.model_validate(observance)


@router.delete(
    "/observances/{observance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a non-person liturgical observance",
)
async def delete_observance(
    observance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("calendar", "delete")),
) -> Response:
    service = CalendarService(db)
    try:
        await service.delete_observance(observance_id)
    except ObservanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/entries",
    response_model=FeastEntrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a calendar assignment",
)
async def create_entry(
    data: FeastEntryCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("calendar", "create")),
) -> FeastEntrySchema:
    service = CalendarService(db)
    try:
        entry = await service.create_entry(data)
    except CalendarNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FeastNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FeastConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return FeastEntrySchema.model_validate(entry)


@router.patch(
    "/entries/{entry_id}",
    response_model=FeastEntrySchema,
    summary="Update a calendar assignment",
)
async def update_entry(
    entry_id: uuid.UUID,
    data: FeastEntryUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("calendar", "update")),
) -> FeastEntrySchema:
    service = CalendarService(db)
    try:
        entry = await service.update_entry(entry_id, data)
    except (CalendarNotFoundError, FeastNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (FeastConflictError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return FeastEntrySchema.model_validate(entry)


@router.delete(
    "/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a calendar assignment",
)
async def delete_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("calendar", "delete")),
) -> Response:
    service = CalendarService(db)
    try:
        await service.delete_entry(entry_id)
    except FeastNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
