"""Protected create endpoints for geography reference data."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.geography_service import GeographyService
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
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


@router.post(
    "/countries",
    response_model=CountrySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create country",
)
async def create_country(
    data: CountryCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("geography", "create")),
) -> CountrySchema:
    country = await GeographyService(db).create_country(data)
    return CountrySchema.model_validate(country)


@router.post(
    "/dioceses",
    response_model=DioceseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create diocese",
)
async def create_diocese(
    data: DioceseCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("geography", "create")),
) -> DioceseSchema:
    diocese = await GeographyService(db).create_diocese(data)
    return DioceseSchema.model_validate(diocese)


@router.post(
    "/places",
    response_model=PlaceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create place",
)
async def create_place(
    data: PlaceCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("geography", "create")),
) -> PlaceSchema:
    place = await GeographyService(db).create_place(data)
    return PlaceSchema.model_validate(place)


@router.post(
    "/churches",
    response_model=ChurchSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create church",
)
async def create_church(
    data: ChurchCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("geography", "create")),
) -> ChurchSchema:
    church = await GeographyService(db).create_church(data)
    return ChurchSchema.model_validate(church)
