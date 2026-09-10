"""Shared persistence helpers for access-control application services."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from src.application.services.access_control_errors import AccessControlNotFoundError
from src.domain.identity.models import Role, RolePermission


class AccessControlBase:
    """Provide shared role lookup without owning the transaction boundary."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _role_query() -> Select[tuple[Role]]:
        return (
            select(Role)
            .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
            .execution_options(populate_existing=True)
        )

    async def _get_role(self, role_id: uuid.UUID, *, for_update: bool = False) -> Role:
        query = self._role_query().where(Role.id == role_id, Role.deleted_at.is_(None))
        if for_update:
            query = query.with_for_update()
        role = (await self.db.execute(query)).scalar_one_or_none()
        if role is None:
            raise AccessControlNotFoundError("Rola nie istnieje")
        return role
