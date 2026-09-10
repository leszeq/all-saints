"""Application service for roles and permission assignments."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.exc import IntegrityError

from src.application.services.access_control_base import AccessControlBase
from src.application.services.access_control_errors import (
    AccessControlConflictError,
    AccessControlValidationError,
)
from src.domain.identity.models import (
    Permission,
    Role,
    RolePermission,
    SystemRole,
    User,
    UserRole,
)
from src.domain.identity.rbac import (
    ALL_PERMISSION_KEYS,
    CUSTOM_ROLE_PERMISSION_KEYS,
    split_permission_key,
)


class RoleAccessControlService(AccessControlBase):
    """Manage roles and permissions inside a caller-owned transaction."""

    async def list_roles(self) -> tuple[Sequence[Role], dict[uuid.UUID, int]]:
        roles = (
            (
                await self.db.execute(
                    self._role_query()
                    .where(Role.deleted_at.is_(None))
                    .order_by(Role.is_system.desc(), Role.display_name.asc())
                )
            )
            .scalars()
            .all()
        )
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
            await self.db.flush()
        except IntegrityError as exc:
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
            await self.db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
            self._assign_permissions(role, permissions)
        role.version += 1
        role.updated_at = datetime.now(UTC)
        await self.db.flush()
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
            raise AccessControlConflictError("Nie można usunąć roli przypisanej do użytkowników")
        role.deleted_at = datetime.now(UTC)
        role.version += 1
        await self.db.flush()

    async def _resolve_custom_permissions(
        self,
        permission_keys: set[str],
    ) -> Sequence[Permission]:
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
            (
                await self.db.execute(
                    select(Permission).where(
                        tuple_(Permission.resource, Permission.action).in_(pairs),
                        Permission.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        found = {f"{permission.resource}:{permission.action}" for permission in permissions}
        missing = permission_keys - found
        if missing:
            raise AccessControlConflictError(
                "Macierz uprawnień nie została zsynchronizowana: " + ", ".join(sorted(missing))
            )
        return permissions

    def _assign_permissions(
        self,
        role: Role,
        permissions: Sequence[Permission],
    ) -> None:
        now = datetime.now(UTC)
        for permission in permissions:
            self.db.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                    granted_at=now,
                )
            )
