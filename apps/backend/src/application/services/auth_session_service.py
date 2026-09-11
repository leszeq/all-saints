"""Authentication session rotation and revocation use cases."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.services.audit_service import AuditContext, add_audit_log
from src.core.security import JWTService, jwt_service
from src.domain.identity.models import AuditAction, RefreshToken, User, UserRole


class InvalidRefreshTokenError(ValueError):
    """Raised when a refresh token cannot start a session rotation."""


class InactiveSessionAccountError(ValueError):
    """Raised when the refresh token belongs to an inactive account."""


class LockedSessionAccountError(ValueError):
    """Raised when the refresh token belongs to a temporarily locked account."""


@dataclass(frozen=True, slots=True)
class RotatedSession:
    """New credentials returned after atomically rotating a refresh token."""

    access_token: str
    refresh_token: str


class AuthenticationSessionService:
    """Own refresh-token state changes inside a caller-managed transaction."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        token_service: JWTService = jwt_service,
    ) -> None:
        self.db = db
        self._token_service = token_service

    async def start(
        self,
        user: User,
        *,
        audit_context: AuditContext,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RotatedSession:
        """Stage the initial refresh token and login audit for a user."""
        raw_token, token_hash = self._token_service.create_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=self._token_service.get_token_expiry("refresh"),
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )
        add_audit_log(
            self.db,
            context=replace(
                audit_context,
                user_id=user.id,
                user_email=user.email,
            ),
            action=AuditAction.LOGIN,
            resource_type="authentication",
            resource_id=user.id,
        )
        await self.db.flush()
        role_names = [user_role.role.name for user_role in user.roles if user_role.role]
        return RotatedSession(
            access_token=self._token_service.create_access_token(
                user_id=user.id,
                email=user.email,
                roles=role_names,
                password_changed_at=user.password_changed_at,
            ),
            refresh_token=raw_token,
        )

    async def rotate(
        self,
        raw_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RotatedSession:
        """Consume one valid refresh token and issue a replacement session."""
        token_hash = self._token_service.hash_refresh_token(raw_token)
        stored_token = (
            await self.db.execute(
                select(RefreshToken)
                .options(
                    selectinload(RefreshToken.user)
                    .selectinload(User.roles)
                    .selectinload(UserRole.role)
                )
                .where(RefreshToken.token_hash == token_hash)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if stored_token is None or not stored_token.is_valid:
            raise InvalidRefreshTokenError

        user = stored_token.user
        if not user.is_active:
            raise InactiveSessionAccountError
        if user.is_locked:
            raise LockedSessionAccountError

        role_names = [user_role.role.name for user_role in user.roles if user_role.role]
        new_raw_token, new_token_hash = self._token_service.create_refresh_token()
        stored_token.revoked_at = datetime.now(UTC)
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=new_token_hash,
                expires_at=self._token_service.get_token_expiry("refresh"),
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )
        await self.db.flush()

        return RotatedSession(
            access_token=self._token_service.create_access_token(
                user_id=user.id,
                email=user.email,
                roles=role_names,
                password_changed_at=user.password_changed_at,
            ),
            refresh_token=new_raw_token,
        )

    async def revoke(
        self,
        raw_token: str,
        *,
        audit_context: AuditContext,
    ) -> bool:
        """Revoke a refresh token when present and record the logout event."""
        token_hash = self._token_service.hash_refresh_token(raw_token)
        stored_token = (
            await self.db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        ).scalar_one_or_none()
        if stored_token is None:
            return False

        stored_token.revoked_at = datetime.now(UTC)
        add_audit_log(
            self.db,
            context=replace(audit_context, user_id=stored_token.user_id),
            action=AuditAction.LOGOUT,
            resource_type="authentication",
            resource_id=stored_token.user_id,
        )
        await self.db.flush()
        return True

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        *,
        revoked_at: datetime | None = None,
    ) -> None:
        """Invalidate every active refresh token owned by one user."""
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at or datetime.now(UTC))
        )
