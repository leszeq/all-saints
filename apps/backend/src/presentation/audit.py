"""Translate authenticated HTTP request state into application audit context."""

from fastapi import Request

from src.application.services.audit_service import AuditContext
from src.domain.identity.models import User


def audit_context_from_request(request: Request, user: User) -> AuditContext:
    """Build a safe audit context without copying credentials or request bodies."""
    return AuditContext(
        user_id=user.id,
        user_email=user.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        request_id=getattr(request.state, "request_id", None),
    )
