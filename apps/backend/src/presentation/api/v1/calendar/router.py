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
)

router = APIRouter()


def _day_response(
    value: date,
    calendar: LiturgicalCalendar,
    entries: list[Feast],
    *,
    include_universal: bool,
) -> CalendarDaySchema:
    serialized = [FeastEntrySchema.model_validate(entry) for entry in entries]
    return CalendarDaySchema(
        date=value,
        calendar_code=calendar.code,
        calendar_name=calendar.name,
        includes_universal=include_universal and calendar.code != "roman_universal",
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
    "/today",
    response_model=CalendarDaySchema,
    summary="Get today's commemorations",
    description="Uses the Europe/Warsaw civil date and merges the selected calendar with the universal one.",
)
async def get_today(
    calendar_code: str = Query("roman_pl", max_length=50),
    include_universal: bool = True,
    db: AsyncSession = Depends(get_db_session),
) -> CalendarDaySchema:
    value = datetime.now(ZoneInfo("Europe/Warsaw")).date()
    return await _get_day_response(value, calendar_code, include_universal, db)


@router.get(
    "/day/{value}",
    response_model=CalendarDaySchema,
    summary="Get all commemorations for a date",
)
async def get_day(
    value: date,
    calendar_code: str = Query("roman_pl", max_length=50),
    include_universal: bool = True,
    db: AsyncSession = Depends(get_db_session),
) -> CalendarDaySchema:
    return await _get_day_response(value, calendar_code, include_universal, db)


async def _get_day_response(
    value: date,
    calendar_code: str,
    include_universal: bool,
    db: AsyncSession,
) -> CalendarDaySchema:
    service = CalendarService(db)
    try:
        calendar, entries = await service.get_day(
            value,
            calendar_code=calendar_code,
            include_universal=include_universal,
        )
    except CalendarNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _day_response(
        value,
        calendar,
        entries,
        include_universal=include_universal,
    )


@router.get(
    "/month/{year}/{month}",
    response_model=CalendarMonthSchema,
    summary="Get a complete civil month with liturgical assignments",
    description="Returns every day of the month, including empty dates and 29 February in leap years.",
)
async def get_month(
    year: Annotated[int, Path(ge=1900, le=2200)],
    month: Annotated[int, Path(ge=1, le=12)],
    calendar_code: str = Query("roman_pl", max_length=50),
    include_universal: bool = True,
    db: AsyncSession = Depends(get_db_session),
) -> CalendarMonthSchema:
    service = CalendarService(db)
    try:
        selected, grouped = await service.get_month(
            year=year,
            month=month,
            calendar_code=calendar_code,
            include_universal=include_universal,
        )
    except (CalendarNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    days = [
        _day_response(
            date(year, month, day),
            selected,
            grouped.get(day, []),
            include_universal=include_universal,
        )
        for day in range(1, civil_calendar.monthrange(year, month)[1] + 1)
    ]
    return CalendarMonthSchema(
        year=year,
        month=month,
        calendar_code=selected.code,
        calendar_name=selected.name,
        includes_universal=include_universal and selected.code != "roman_universal",
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
