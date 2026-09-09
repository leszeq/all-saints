"""Aggregate public and editorial liturgical calendar routes."""

from fastapi import APIRouter

from src.presentation.api.v1.calendar.editorial import (
    create_entry,
    create_observance,
    delete_entry,
    delete_observance,
    list_person_entries,
    update_entry,
    update_observance,
)
from src.presentation.api.v1.calendar.editorial import router as editorial_router
from src.presentation.api.v1.calendar.public import (
    get_day,
    get_month,
    get_observance,
    get_today,
    list_calendars,
    list_observances,
)
from src.presentation.api.v1.calendar.public import router as public_router

router = APIRouter()
router.include_router(public_router)
router.include_router(editorial_router)

__all__ = [
    "create_entry",
    "create_observance",
    "delete_entry",
    "delete_observance",
    "get_day",
    "get_month",
    "get_observance",
    "get_today",
    "list_calendars",
    "list_observances",
    "list_person_entries",
    "update_entry",
    "update_observance",
]
