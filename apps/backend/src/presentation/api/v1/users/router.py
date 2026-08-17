"""
Users management API endpoints (Admin only).

Endpoints:
- GET    /users          – List all users (paginated)
- POST   /users          – Create a new user
- GET    /users/{id}     – Get user details
- PATCH  /users/{id}     – Update user
- DELETE /users/{id}     – Soft-delete user
- POST   /users/{id}/roles  – Assign role
- DELETE /users/{id}/roles/{role_id} – Remove role
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.security import is_strong_password, password_hasher
from src.domain.identity.models import Role, User, UserRole, UserStatus
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import get_current_user, require_permission

router = APIRouter()


# ==============================================================================
# SCHEMAS
# ==============================================================================


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=300)
    preferred_language: str = Field(default="pl", max_length=10)


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=300)
    status: UserStatus | None = None
    preferred_language: str | None = Field(None, max_length=10)
    bio: str | None = None


class UserListItem(BaseModel):
    id: str
    email: str
    full_name: str
    status: str
    roles: list[str]
    created_at: datetime
    last_login_at: datetime | None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    per_page: int
    pages: int


# ==============================================================================
# ENDPOINTS
# ==============================================================================


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
)
async def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = Query(None, max_length=200),
    status: UserStatus | None = None,
    db: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("users", "read")),
) -> UserListResponse:
    """List all users with optional filtering and pagination."""
    query = (
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.deleted_at.is_(None))
    )

    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
        )
    if status:
        query = query.where(User.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    result = await db.execute(
        query.order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    users = result.scalars().all()

    items = [
        UserListItem(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            status=u.status,
            roles=[ur.role.name for ur in u.roles if ur.role],
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )
        for u in users
    ]

    return UserListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=-(-total // per_page),  # Ceiling division
    )


@router.post(
    "",
    response_model=UserListItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
async def create_user(
    data: CreateUserRequest,
    db: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("users", "create")),
) -> UserListItem:
    """Create a new user account."""
    # Check uniqueness
    existing = await db.execute(
        select(User).where(User.email == data.email.lower()).where(User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Użytkownik z adresem {data.email} już istnieje",
        )

    # Validate password
    is_strong, errors = is_strong_password(data.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Hasło jest zbyt słabe", "errors": errors},
        )

    user = User(
        email=data.email.lower(),
        hashed_password=password_hasher.hash(data.password),
        full_name=data.full_name,
        preferred_language=data.preferred_language,
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserListItem(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        roles=[],
        created_at=user.created_at,
        last_login_at=None,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Delete user",
)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_admin: User = Depends(require_permission("users", "delete")),
) -> None:
    """Soft-delete a user account."""
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nie możesz usunąć własnego konta",
        )

    result = await db.execute(
        select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Użytkownik nie znaleziony")

    user.deleted_at = datetime.now(timezone.utc)
    await db.commit()
