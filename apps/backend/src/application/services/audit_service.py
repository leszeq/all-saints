"""Immutable audit-trail helpers for data-modifying application services."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.identity.models import AuditAction, AuditLog


@dataclass(frozen=True, slots=True)
class AuditContext:
    """Authenticated actor and safe request metadata attached to an audit row."""

    user_id: uuid.UUID | None = None
    user_email: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None

    @classmethod
    def for_user(cls, user_id: uuid.UUID | None) -> AuditContext:
        return cls(user_id=user_id)


def add_audit_log(
    db: AsyncSession,
    *,
    context: AuditContext,
    action: AuditAction,
    resource_type: str,
    resource_id: uuid.UUID | None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Stage an audit row in the caller's transaction without committing it."""
    audit_log = AuditLog(
        user_id=context.user_id,
        user_email=context.user_email,
        action=action.value,
        resource_type=resource_type,
        resource_id=resource_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=context.ip_address,
        user_agent=context.user_agent[:500] if context.user_agent else None,
        request_id=context.request_id[:36] if context.request_id else None,
        extra_metadata=extra_metadata,
    )
    db.add(audit_log)
    return audit_log
