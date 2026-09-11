"""Credential authentication and initial session issuance use case."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.audit_service import AuditContext
from src.application.services.auth_security_service import AuthenticationSecurityRecorder
from src.application.services.auth_session_service import (
    AuthenticationSessionService,
    RotatedSession,
)
from src.application.services.auth_user_query_service import AuthenticationUserQueryService
from src.core.security import password_hasher
from src.domain.identity.models import UserStatus


class InvalidLoginCredentialsError(ValueError):
    """Raised when the supplied email and password do not identify a user."""


class BannedLoginAccountError(ValueError):
    """Raised when a banned account attempts to log in."""


class LockedLoginAccountError(ValueError):
    """Raised when a temporarily locked account attempts to log in."""


class AuthenticationLoginService:
    """Authenticate credentials while preserving durable denial records."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        security_recorder: AuthenticationSecurityRecorder,
    ) -> None:
        self.db = db
        self._security_recorder = security_recorder
        self._users = AuthenticationUserQueryService(db)
        self._sessions = AuthenticationSessionService(db)

    async def authenticate(
        self,
        *,
        email: str,
        password: str,
        audit_context: AuditContext,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RotatedSession:
        """Validate credentials and stage a new refresh-token session."""
        normalized_email = email.strip().lower()
        user = await self._users.find_by_email(normalized_email)
        if user is None:
            await self._security_recorder.record_login_failure(
                context=replace(audit_context, user_email=normalized_email),
                reason="invalid_credentials",
            )
            raise InvalidLoginCredentialsError

        identified_context = replace(
            audit_context,
            user_id=user.id,
            user_email=user.email,
        )
        if user.status == UserStatus.BANNED:
            await self._security_recorder.record_login_failure(
                context=identified_context,
                reason="account_banned",
            )
            raise BannedLoginAccountError

        if user.is_locked:
            await self._security_recorder.record_login_failure(
                context=identified_context,
                reason="account_locked",
            )
            raise LockedLoginAccountError

        if not password_hasher.verify(password, user.hashed_password):
            account_locked = await self._security_recorder.record_login_failure(
                context=identified_context,
                reason="invalid_credentials",
                increment_attempts=True,
            )
            if account_locked:
                logger.warning(f"Account locked: {user.email} (too many failed attempts)")
            raise InvalidLoginCredentialsError

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)
        session = await self._sessions.start(
            user,
            audit_context=identified_context,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        logger.info(f"User logged in: {user.email}")
        return session
