"""Database-backed identity queries used by authentication use cases."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.identity.models import Role, RolePermission, User, UserRole


def _user_with_access_control() -> Select[tuple[User]]:
    return select(User).options(
        selectinload(User.roles)
        .selectinload(UserRole.role)
        .selectinload(Role.permissions)
        .selectinload(RolePermission.permission)
    )


class AuthenticationUserQueryService:
    """Load non-deleted users with their complete RBAC projection."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_email(self, email: str) -> User | None:
        """Find a user by normalized email for credential authentication."""
        return (
            await self.db.execute(
                _user_with_access_control()
                .where(User.email == email.strip().lower())
                .where(User.deleted_at.is_(None))
            )
        ).scalar_one_or_none()

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        """Find a user by identifier for Bearer-token authentication."""
        return (
            await self.db.execute(
                _user_with_access_control()
                .where(User.id == user_id)
                .where(User.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
