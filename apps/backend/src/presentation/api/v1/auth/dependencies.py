"""Authentication and authorization dependencies shared by API routers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.security import jwt_service
from src.domain.identity.models import Role, RolePermission, User, UserRole
from src.infrastructure.db.session import get_db_session

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT otrzymany z endpointu POST /api/v1/auth/login",
)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Validate a Bearer token and load its active, unlocked user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Wymagane uwierzytelnienie",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise credentials_exception

    token = credentials.credentials.strip()
    if not token:
        raise credentials_exception

    try:
        payload = jwt_service.verify_access_token(token)
    except InvalidTokenError:
        raise credentials_exception from None

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles)
            .selectinload(UserRole.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission)
        )
        .where(User.id == payload.user_id)
        .where(User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None or not payload.matches_password_version(user.password_changed_at):
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto jest nieaktywne",
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto jest tymczasowo zablokowane",
        )

    request.state.user_id = str(user.id)
    request.state.user_email = user.email
    return user


def require_permission(resource: str, action: str) -> Callable[..., Awaitable[User]]:
    """Build a dependency that requires one database-backed permission."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Brak uprawnień: {resource}:{action}",
            )
        return user

    return _check
