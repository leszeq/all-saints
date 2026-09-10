"""Geography API composition and backwards-compatible exports."""

from fastapi import APIRouter

from src.presentation.api.v1.geography.editorial import (
    create_church,
    create_country,
    create_diocese,
    create_place,
)
from src.presentation.api.v1.geography.editorial import router as editorial_router
from src.presentation.api.v1.geography.public import (
    list_churches,
    list_countries,
    list_dioceses,
    list_places,
)
from src.presentation.api.v1.geography.public import router as public_router
from src.presentation.api.v1.geography.schemas import (
    ChurchCreateSchema,
    ChurchSchema,
    CountryCreateSchema,
    CountrySchema,
    DioceseCreateSchema,
    DioceseSchema,
    PlaceCreateSchema,
    PlaceSchema,
)

router = APIRouter()
router.include_router(public_router)
router.include_router(editorial_router)

__all__ = [
    "ChurchCreateSchema",
    "ChurchSchema",
    "CountryCreateSchema",
    "CountrySchema",
    "DioceseCreateSchema",
    "DioceseSchema",
    "PlaceCreateSchema",
    "PlaceSchema",
    "create_church",
    "create_country",
    "create_diocese",
    "create_place",
    "list_churches",
    "list_countries",
    "list_dioceses",
    "list_places",
]
