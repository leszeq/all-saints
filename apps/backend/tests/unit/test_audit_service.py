"""Unit coverage for staging immutable audit records."""

from unittest.mock import MagicMock
from uuid import uuid4

from src.application.services.audit_service import AuditContext, add_audit_log
from src.domain.identity.models import AuditAction, AuditLog


def test_audit_record_keeps_safe_context_and_never_commits() -> None:
    db = MagicMock()
    user_id = uuid4()
    resource_id = uuid4()

    result = add_audit_log(
        db,
        context=AuditContext(
            user_id=user_id,
            user_email="editor@example.org",
            ip_address="127.0.0.1",
            user_agent="a" * 600,
            request_id="request-id-that-is-deliberately-longer-than-the-column",
        ),
        action=AuditAction.UPDATE,
        resource_type="persons",
        resource_id=resource_id,
        old_value={"status": "draft"},
        new_value={"status": "review"},
    )

    assert isinstance(result, AuditLog)
    assert result.user_id == user_id
    assert result.resource_id == resource_id
    assert len(result.user_agent) == 500
    assert len(result.request_id) == 36
    db.add.assert_called_once_with(result)
    db.commit.assert_not_called()
