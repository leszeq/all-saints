"""REST API for liturgical calendars and daily saint commemorations."""

from __future__ import annotations

import calendar as civil_calendar
import uuid
from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
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
from src.domain.liturgy.models import Feast, LiturgicalCalendar
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.calendar.schemas import (
    CalendarDaySchema,
    CalendarMonthSchema,
    FeastEntryCreateSchema,
    FeastEntrySchema,
    FeastEntryUpdateSchema,
    LiturgicalCalendarSchema,
    LiturgicalObservanceCreateSchema,
    LiturgicalObservanceSchema,
    LiturgicalObservanceUpdateSchema,
)

router = APIRouter()


def _day_response(
    value: date,
    calendar: LiturgicalCalendar,
    entries: list[Feast],
    *,
    include_universal: bool,
    include_martyrology: bool,
) -> CalendarDaySchema:
    serialized = [FeastEntrySchema.model_validate(entry) for entry in entries]
    return CalendarDaySchema(
        date=value,
        calendar_code=calendar.code,
        calendar_name=calendar.name,
        includes_universal=include_universal and calendar.code != "roman_universal",
        includes_martyrology=(
            include_martyrology and calendar.code != "roman_martyrology"
        ),
        primary=serialized[0] if serialized else None,
        entries=serialized,
        total=len(serialized),
    )


@router.get(
    "/calendars",
    response_model=list[LiturgicalCalendarSchema],
    summary="List available liturgical calendars",
)
async def list_calendars(
    db: AsyncSession = Depends(get_db_session),
) -> list[LiturgicalCalendarSchema]:
    service = CalendarService(db)
    return [
        LiturgicalCalendarSchema.model_validate(calendar)
        for calendar in await service.list_calendars()
    ]


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


@router.get(
    "/observances",
    response_model=list[LiturgicalObservanceSchema],
    summary="List non-person liturgical observances",
)
async def list_observances(
    db: AsyncSession = Depends(get_db_session),
) -> list[LiturgicalObservanceSchema]:
    service = CalendarService(db)
    return [
        LiturgicalObservanceSchema.model_validate(observance)
        for observance in await service.list_observances()
    ]


@router.get(
    "/observances/by-slug/{slug}",
    response_model=LiturgicalObservanceSchema,
    summary="Get a non-person liturgical observance",
)
async def get_observance(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> LiturgicalObservanceSchema:
    service = CalendarService(db)
    try:
        observance = await service.get_observance(slug)
    except ObservanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LiturgicalObservanceSchema.model_validate(observance)


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


@router.get(
    "/today",
    response_model=CalendarDaySchema,
    summary="Get today's commemorations",
    description="Uses the Europe/Warsaw civil date and merges the selected calendar with the universal one.",
)
async def get_today(
    calendar_code: str = Query("roman_pl", max_length=50),
    include_universal: bool = True,
    include_martyrology: bool = True,
    db: AsyncSession = Depends(get_db_session),
) -> CalendarDaySchema:
    value = datetime.now(ZoneInfo("Europe/Warsaw")).date()
    return await _get_day_response(
        value,
        calendar_code,
        include_universal,
        include_martyrology,
        db,
    )


@router.get(
    "/day/{value}",
    response_model=CalendarDaySchema,
    summary="Get all commemorations for a date",
    description="Returns resolved fixed-date assignments. Moveable rules are not accepted by the current API.",
)
async def get_day(
    value: date,
    calendar_code: str = Query("roman_pl", max_length=50),
    include_universal: bool = True,
    include_martyrology: bool = True,
    db: AsyncSession = Depends(get_db_session),
) -> CalendarDaySchema:
    return await _get_day_response(
        value,
        calendar_code,
        include_universal,
        include_martyrology,
        db,
    )


async def _get_day_response(
    value: date,
    calendar_code: str,
    include_universal: bool,
    include_martyrology: bool,
    db: AsyncSession,
) -> CalendarDaySchema:
    service = CalendarService(db)
    try:
        calendar, entries = await service.get_day(
            value,
            calendar_code=calendar_code,
            include_universal=include_universal,
            include_martyrology=include_martyrology,
        )
    except CalendarNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _day_response(
        value,
        calendar,
        entries,
        include_universal=include_universal,
        include_martyrology=include_martyrology,
    )


@router.get(
    "/month/{year}/{month}",
    response_model=CalendarMonthSchema,
    summary="Get a complete civil month with liturgical assignments",
    description=(
        "Returns every day of the month, including empty dates and 29 February in "
        "leap years. Only resolved fixed-date assignments are included."
    ),
)
async def get_month(
    year: Annotated[int, Path(ge=1900, le=2200)],
    month: Annotated[int, Path(ge=1, le=12)],
    calendar_code: str = Query("roman_pl", max_length=50),
    include_universal: bool = True,
    include_martyrology: bool = True,
    db: AsyncSession = Depends(get_db_session),
) -> CalendarMonthSchema:
    service = CalendarService(db)
    try:
        selected, grouped = await service.get_month(
            year=year,
            month=month,
            calendar_code=calendar_code,
            include_universal=include_universal,
            include_martyrology=include_martyrology,
        )
    except (CalendarNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    days = [
        _day_response(
            date(year, month, day),
            selected,
            grouped.get(day, []),
            include_universal=include_universal,
            include_martyrology=include_martyrology,
        )
        for day in range(1, civil_calendar.monthrange(year, month)[1] + 1)
    ]
    return CalendarMonthSchema(
        year=year,
        month=month,
        calendar_code=selected.code,
        calendar_name=selected.name,
        includes_universal=include_universal and selected.code != "roman_universal",
        includes_martyrology=(
            include_martyrology and selected.code != "roman_martyrology"
        ),
        days=days,
    )


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
