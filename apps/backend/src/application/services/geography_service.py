"""Application service for geography reference data."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.geography import (
    CreateChurchCommand,
    CreateCountryCommand,
    CreateDioceseCommand,
    CreatePlaceCommand,
)
from src.application.services.pagination import execute_page
from src.domain.geography.models import Church, Country, Diocese, Place


class GeographyService:
    """Read and create geography records inside a caller-owned transaction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_countries(self, *, search: str | None = None) -> list[Country]:
        """Return active countries ordered by their Polish name."""
        statement = select(Country).where(Country.deleted_at.is_(None))
        if search:
            statement = statement.where(
                Country.name_pl.ilike(f"%{search}%") | Country.name_en.ilike(f"%{search}%")
            )
        result = await self.db.execute(statement.order_by(Country.name_pl.asc()))
        return list(result.scalars().all())

    async def create_country(self, data: CreateCountryCommand) -> Country:
        """Create a country without committing the caller's unit of work."""
        country = Country(**data.model_dump())
        self.db.add(country)
        await self.db.flush()
        await self.db.refresh(country)
        return country

    async def list_dioceses(
        self,
        *,
        country_id: uuid.UUID | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Diocese], int]:
        """Return one page of active dioceses."""
        statement = select(Diocese).where(Diocese.deleted_at.is_(None))
        if country_id:
            statement = statement.where(Diocese.country_id == country_id)
        return await execute_page(
            self.db,
            statement.order_by(Diocese.name.asc()),
            page=page,
            per_page=per_page,
        )

    async def create_diocese(self, data: CreateDioceseCommand) -> Diocese:
        """Create a diocese without committing the caller's unit of work."""
        diocese = Diocese(**data.model_dump())
        self.db.add(diocese)
        await self.db.flush()
        await self.db.refresh(diocese)
        return diocese

    async def list_places(
        self,
        *,
        country_id: uuid.UUID | None = None,
        search: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Place], int]:
        """Return one filtered page of active places."""
        statement = select(Place).where(Place.deleted_at.is_(None))
        if country_id:
            statement = statement.where(Place.country_id == country_id)
        if search:
            statement = statement.where(Place.name.ilike(f"%{search}%"))
        return await execute_page(
            self.db,
            statement.order_by(Place.name.asc()),
            page=page,
            per_page=per_page,
        )

    async def create_place(self, data: CreatePlaceCommand) -> Place:
        """Create a place without committing the caller's unit of work."""
        place = Place(**data.model_dump())
        self.db.add(place)
        await self.db.flush()
        await self.db.refresh(place)
        return place

    async def list_churches(
        self,
        *,
        place_id: uuid.UUID | None = None,
        is_sanctuary: bool | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Church], int]:
        """Return one filtered page of active churches."""
        statement = select(Church).where(Church.deleted_at.is_(None))
        if place_id:
            statement = statement.where(Church.place_id == place_id)
        if is_sanctuary is not None:
            statement = statement.where(Church.is_national_sanctuary == is_sanctuary)
        return await execute_page(
            self.db,
            statement.order_by(Church.name.asc()),
            page=page,
            per_page=per_page,
        )

    async def create_church(self, data: CreateChurchCommand) -> Church:
        """Create a church without committing the caller's unit of work."""
        church = Church(**data.model_dump())
        self.db.add(church)
        await self.db.flush()
        await self.db.refresh(church)
        return church
