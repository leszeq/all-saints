"""Protected user-management queries."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.user_access_control_service import UserAccessControlService
from src.domain.identity.models import User, UserStatus
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.users.responses import serialize_user
from src.presentation.api.v1.users.schemas import UserListResponseSchema


async def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = Query(None, max_length=200),
    status_filter: UserStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db_session),
    _super_admin: User = Depends(require_permission("users", "read")),
) -> UserListResponseSchema:
    """Return one filtered page of managed user accounts."""
    users, total = await UserAccessControlService(db).list_users(
        page=page,
        per_page=per_page,
        search=search,
        status=status_filter,
    )
    return UserListResponseSchema(
        items=[serialize_user(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, -(-total // per_page)),
    )
