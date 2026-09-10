"""Application service for taxonomy reference data."""

from __future__ import annotations

import uuid
from typing import TypeVar

from slugify import slugify
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.taxonomy import CreateCategoryCommand, CreateTagCommand
from src.domain.hagiography.models import Category, Occupation, StateOfLife, Tag

T = TypeVar("T")


class TaxonomyService:
    """Read and create taxonomy records inside a caller-owned transaction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_categories(
        self,
        *,
        parent_id: uuid.UUID | None = None,
    ) -> list[Category]:
        """Return active categories in editorial display order."""
        statement = select(Category).where(Category.deleted_at.is_(None))
        if parent_id is not None:
            statement = statement.where(Category.parent_id == parent_id)
        result = await self.db.execute(
            statement.order_by(Category.sort_order.asc(), Category.name_pl.asc())
        )
        return list(result.scalars().all())

    async def create_category(self, data: CreateCategoryCommand) -> Category:
        """Create a category with a deterministic slug."""
        category = Category(slug=slugify(data.name_pl), **data.model_dump())
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def list_tags(
        self,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Tag], int]:
        """Return one filtered page of active tags."""
        statement = select(Tag).where(Tag.deleted_at.is_(None))
        if search:
            statement = statement.where(
                Tag.name_pl.ilike(f"%{search}%") | Tag.name_en.ilike(f"%{search}%")
            )
        return await self._execute_page(
            statement.order_by(Tag.name_pl.asc()),
            page=page,
            per_page=per_page,
        )

    async def create_tag(self, data: CreateTagCommand) -> Tag:
        """Create a tag with a deterministic slug."""
        tag = Tag(slug=slugify(data.name_pl), **data.model_dump())
        self.db.add(tag)
        await self.db.flush()
        await self.db.refresh(tag)
        return tag

    async def list_states_of_life(self) -> list[StateOfLife]:
        """Return the complete active state-of-life dictionary."""
        statement = (
            select(StateOfLife)
            .where(StateOfLife.deleted_at.is_(None))
            .order_by(StateOfLife.name_pl.asc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def list_occupations(
        self,
        *,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Occupation], int]:
        """Return one page of active occupations."""
        statement = (
            select(Occupation)
            .where(Occupation.deleted_at.is_(None))
            .order_by(Occupation.name_pl.asc())
        )
        return await self._execute_page(statement, page=page, per_page=per_page)

    async def _execute_page(
        self,
        statement: Select[tuple[T]],
        *,
        page: int,
        per_page: int,
    ) -> tuple[list[T], int]:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = int((await self.db.execute(count_statement)).scalar_one())
        result = await self.db.execute(statement.offset((page - 1) * per_page).limit(per_page))
        return list(result.scalars().all()), total
