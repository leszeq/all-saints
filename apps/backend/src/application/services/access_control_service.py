"""Application service for user accounts, roles, and permission assignments."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from src.core.security import is_strong_password, password_hasher
from src.domain.identity.models import (
    Permission,
    Role,
    RolePermission,
    SystemRole,
    User,
    UserRole,
    UserStatus,
)
from src.domain.identity.rbac import (
    ALL_PERMISSION_KEYS,
    CUSTOM_ROLE_PERMISSION_KEYS,
    split_permission_key,
)


class AccessControlNotFoundError(ValueError):
    """Raised when a managed user or role does not exist."""


class AccessControlConflictError(ValueError):
    """Raised when a unique or assignment invariant would be violated."""


class AccessControlValidationError(ValueError):
    """Raised when input violates the access-control policy."""


class AccessControlService:
    """Manage identities without exposing persistence details to API routers."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _user_query() -> Select[tuple[User]]:
        return select(User).options(
            selectinload(User.roles).selectinload(UserRole.role)
        ).execution_options(populate_existing=True)

    @staticmethod
    def _role_query() -> Select[tuple[Role]]:
        return select(Role).options(
            selectinload(Role.permissions).selectinload(RolePermission.permission)
        ).execution_options(populate_existing=True)

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
            query.order_by(User.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
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
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
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
        await self.db.commit()
        return await self._get_user(user.id)

    async def delete_user(self, user_id: uuid.UUID, *, actor_id: uuid.UUID) -> None:
        user = await self._get_user(user_id, for_update=True)
        self._ensure_managed_user(user, actor_id=actor_id)
        user.deleted_at = datetime.now(UTC)
        user.status = UserStatus.INACTIVE
        user.version += 1
        await self.db.commit()

    async def list_roles(self) -> tuple[Sequence[Role], dict[uuid.UUID, int]]:
        roles = (
            await self.db.execute(
                self._role_query()
                .where(Role.deleted_at.is_(None))
                .order_by(Role.is_system.desc(), Role.display_name.asc())
            )
        ).scalars().all()
        counts_result = await self.db.execute(
            select(UserRole.role_id, func.count(UserRole.user_id))
            .join(User, User.id == UserRole.user_id)
            .where(User.deleted_at.is_(None))
            .group_by(UserRole.role_id)
        )
        user_counts: dict[uuid.UUID, int] = {}
        for role_id, count in counts_result:
            user_counts[role_id] = count
        return roles, user_counts

    async def create_role(
        self,
        *,
        name: str,
        display_name: str,
        description: str | None,
        permission_keys: set[str],
    ) -> Role:
        normalized_name = name.strip().lower()
        if normalized_name in {role.value for role in SystemRole}:
            raise AccessControlConflictError("Nazwa jest zarezerwowana dla roli systemowej")
        existing = (
            await self.db.execute(select(Role.id).where(Role.name == normalized_name))
        ).scalar_one_or_none()
        if existing is not None:
            raise AccessControlConflictError("Rola o tej nazwie już istnieje")

        permissions = await self._resolve_custom_permissions(permission_keys)
        role = Role(
            name=normalized_name,
            display_name=display_name.strip(),
            description=description.strip() if description else None,
            is_system=False,
        )
        self.db.add(role)
        try:
            await self.db.flush()
            self._assign_permissions(role, permissions)
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise AccessControlConflictError("Nie udało się utworzyć unikalnej roli") from exc
        return await self._get_role(role.id)

    async def update_role(
        self,
        role_id: uuid.UUID,
        *,
        display_name: str | None = None,
        description: str | None = None,
        permission_keys: set[str] | None = None,
    ) -> Role:
        role = await self._get_role(role_id, for_update=True)
        if role.is_system:
            raise AccessControlConflictError("Ról systemowych nie można modyfikować")
        if display_name is not None:
            role.display_name = display_name.strip()
        if description is not None:
            role.description = description.strip() or None
        if permission_keys is not None:
            permissions = await self._resolve_custom_permissions(permission_keys)
            await self.db.execute(
                delete(RolePermission).where(RolePermission.role_id == role.id)
            )
            self._assign_permissions(role, permissions)
        role.version += 1
        role.updated_at = datetime.now(UTC)
        await self.db.commit()
        return await self._get_role(role.id)

    async def delete_role(self, role_id: uuid.UUID) -> None:
        role = await self._get_role(role_id, for_update=True)
        if role.is_system:
            raise AccessControlConflictError("Ról systemowych nie można usuwać")
        assignment_count = (
            await self.db.execute(
                select(func.count()).select_from(UserRole).where(UserRole.role_id == role.id)
            )
        ).scalar_one()
        if assignment_count:
            raise AccessControlConflictError(
                "Nie można usunąć roli przypisanej do użytkowników"
            )
        role.deleted_at = datetime.now(UTC)
        role.version += 1
        await self.db.commit()

    async def _get_user(self, user_id: uuid.UUID, *, for_update: bool = False) -> User:
        query = self._user_query().where(User.id == user_id, User.deleted_at.is_(None))
        if for_update:
            query = query.with_for_update()
        user = (await self.db.execute(query)).scalar_one_or_none()
        if user is None:
            raise AccessControlNotFoundError("Użytkownik nie istnieje")
        return user

    async def _get_role(self, role_id: uuid.UUID, *, for_update: bool = False) -> Role:
        query = self._role_query().where(Role.id == role_id, Role.deleted_at.is_(None))
        if for_update:
            query = query.with_for_update()
        role = (await self.db.execute(query)).scalar_one_or_none()
        if role is None:
            raise AccessControlNotFoundError("Rola nie istnieje")
        return role

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
            raise AccessControlConflictError(
                "Własny profil należy zmieniać w ustawieniach konta"
            )
        if user.has_role(SystemRole.SUPER_ADMIN):
            raise AccessControlConflictError("Konta superadministratora nie można modyfikować")

    async def _resolve_custom_permissions(self, permission_keys: set[str]) -> Sequence[Permission]:
        unknown = permission_keys - ALL_PERMISSION_KEYS
        if unknown:
            raise AccessControlValidationError(
                "Nieznane uprawnienia: " + ", ".join(sorted(unknown))
            )
        protected = permission_keys - CUSTOM_ROLE_PERMISSION_KEYS
        if protected:
            raise AccessControlConflictError(
                "Uprawnienia użytkowników i ról są zarezerwowane dla superadministratora"
            )
        if not permission_keys:
            return []

        pairs = [split_permission_key(key) for key in permission_keys]
        permissions = (
            await self.db.execute(
                select(Permission).where(
                    tuple_(Permission.resource, Permission.action).in_(pairs),
                    Permission.deleted_at.is_(None),
                )
            )
        ).scalars().all()
        found = {f"{permission.resource}:{permission.action}" for permission in permissions}
        missing = permission_keys - found
        if missing:
            raise AccessControlConflictError(
                "Macierz uprawnień nie została zsynchronizowana: " + ", ".join(sorted(missing))
            )
        return permissions

    def _assign_permissions(self, role: Role, permissions: Sequence[Permission]) -> None:
        now = datetime.now(UTC)
        for permission in permissions:
            self.db.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                    granted_at=now,
                )
            )
