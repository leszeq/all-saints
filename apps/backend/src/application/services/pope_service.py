"""Application service for the pope catalogue."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.popes import CreatePopeCommand
from src.domain.hagiography.models import Pope


class PopeService:
    """Read and create pope entries inside a caller-owned transaction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_popes(self, *, search: str | None = None) -> list[Pope]:
        """Return active pope entries in catalogue order."""
        statement = select(Pope).where(Pope.deleted_at.is_(None))
        if search:
            statement = statement.where(
                Pope.papal_name.ilike(f"%{search}%") | Pope.birth_name.ilike(f"%{search}%")
            )
        statement = statement.order_by(
            Pope.regnal_number.desc().nullslast(),
            Pope.created_at.desc(),
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def create_pope(self, data: CreatePopeCommand) -> Pope:
        """Create a pope entry without committing the request transaction."""
        pope = Pope(**data.model_dump())
        self.db.add(pope)
        await self.db.flush()
        await self.db.refresh(pope)
        return pope
