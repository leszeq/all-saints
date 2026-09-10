"""Application service for managed user accounts."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from src.application.services.access_control_base import AccessControlBase
from src.application.services.access_control_errors import (
    AccessControlConflictError,
    AccessControlNotFoundError,
    AccessControlValidationError,
)
from src.core.security import is_strong_password, password_hasher
from src.domain.identity.models import Role, SystemRole, User, UserRole, UserStatus


class UserAccessControlService(AccessControlBase):
    """Manage user identities inside a caller-owned transaction."""

    @staticmethod
    def _user_query() -> Select[tuple[User]]:
        return (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRole.role))
            .execution_options(populate_existing=True)
        )

    async def list_users(
        self,
        *,
        page: int,
        per_page: int,
        search: str | None = None,
        status: UserStatus | None = None,
    ) -> tuple[Sequence[User], int]:
        query = self._user_query().where(User.deleted_at.is_(None))
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
        if status is not None:
            query = query.where(User.status == status)

        total = (
            await self.db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()
        result = await self.db.execute(
            query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        )
        return result.scalars().all(), total

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        role_id: uuid.UUID,
        preferred_language: str,
        actor_id: uuid.UUID,
    ) -> User:
        normalized_email = email.strip().lower()
        existing = (
            await self.db.execute(select(User.id).where(User.email == normalized_email))
        ).scalar_one_or_none()
        if existing is not None:
            raise AccessControlConflictError(
                f"Użytkownik z adresem {normalized_email} już istnieje"
            )

        password_is_strong, password_errors = is_strong_password(password)
        if not password_is_strong:
            raise AccessControlValidationError(
                "Hasło jest zbyt słabe: " + ", ".join(password_errors)
            )
        role = await self._get_assignable_role(role_id)

        user = User(
            email=normalized_email,
            hashed_password=password_hasher.hash(password),
            full_name=full_name.strip(),
            preferred_language=preferred_language.strip().lower(),
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        self.db.add(user)
        try:
            await self.db.flush()
            self.db.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                    assigned_at=datetime.now(UTC),
                    assigned_by_id=actor_id,
                )
            )
            await self.db.flush()
        except IntegrityError as exc:
            raise AccessControlConflictError("Nie udało się utworzyć unikalnego konta") from exc
        return await self._get_user(user.id)

    async def update_user(
        self,
        user_id: uuid.UUID,
        *,
        actor_id: uuid.UUID,
        full_name: str | None = None,
        status: UserStatus | None = None,
        role_id: uuid.UUID | None = None,
        preferred_language: str | None = None,
        bio: str | None = None,
    ) -> User:
        user = await self._get_user(user_id, for_update=True)
        self._ensure_managed_user(user, actor_id=actor_id)

        if full_name is not None:
            user.full_name = full_name.strip()
        if status is not None:
            user.status = status
        if preferred_language is not None:
            user.preferred_language = preferred_language.strip().lower()
        if bio is not None:
            user.bio = bio.strip() or None
        if role_id is not None:
            role = await self._get_assignable_role(role_id)
            await self.db.execute(delete(UserRole).where(UserRole.user_id == user.id))
            self.db.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                    assigned_at=datetime.now(UTC),
                    assigned_by_id=actor_id,
                )
            )
        user.version += 1
        user.updated_at = datetime.now(UTC)
        await self.db.flush()
        return await self._get_user(user.id)

    async def delete_user(self, user_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
        user = await self._get_user(user_id, for_update=True)
        self._ensure_managed_user(user, actor_id=actor_id)
        user.deleted_at = datetime.now(UTC)
        user.status = UserStatus.INACTIVE
        user.version += 1
        await self.db.flush()

    async def _get_user(self, user_id: uuid.UUID, *, for_update: bool = False) -> User:
        query = self._user_query().where(User.id == user_id, User.deleted_at.is_(None))
        if for_update:
            query = query.with_for_update()
        user = (await self.db.execute(query)).scalar_one_or_none()
        if user is None:
            raise AccessControlNotFoundError("Użytkownik nie istnieje")
        return user

    async def _get_assignable_role(self, role_id: uuid.UUID) -> Role:
        role = await self._get_role(role_id)
        if role.name == SystemRole.SUPER_ADMIN:
            raise AccessControlConflictError(
                "Superadministrator jest pojedynczym kontem właściciela i nie może być przypisany"
            )
        return role

    @staticmethod
    def _ensure_managed_user(user: User, *, actor_id: uuid.UUID) -> None:
        if user.id == actor_id:
            raise AccessControlConflictError("Własny profil należy zmieniać w ustawieniach konta")
        if user.has_role(SystemRole.SUPER_ADMIN):
            raise AccessControlConflictError("Konta superadministratora nie można modyfikować")
