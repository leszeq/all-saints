"""Durable authentication security events stored outside request transactions."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.services.audit_service import AuditContext, add_audit_log
from src.domain.identity.models import AuditAction, User


class AuthenticationSecurityRecorder:
    """Persist denied-login events in an explicit isolated transaction."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_login_failure(
        self,
        *,
        context: AuditContext,
        reason: str,
        increment_attempts: bool = False,
    ) -> bool:
        """Record a denial and optionally update the account lockout counter.

        This operation deliberately owns its transaction so the security event
        survives the rollback caused by the endpoint's 401/403 response.
        """
        account_locked = False
        audit_context = context

        async with self._session_factory() as db, db.begin():
            user = None
            if context.user_id is not None:
                user = (
                    await db.execute(
                        select(User).where(User.id == context.user_id).with_for_update()
                    )
                ).scalar_one_or_none()
                if user is None:
                    audit_context = replace(context, user_id=None)

            if user is not None and increment_attempts:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 10:
                    user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
                    account_locked = True

            add_audit_log(
                db,
                context=audit_context,
                action=AuditAction.LOGIN_FAILED,
                resource_type="authentication",
                resource_id=context.user_id if user is not None else None,
                extra_metadata={"reason": reason},
            )

        return account_locked
