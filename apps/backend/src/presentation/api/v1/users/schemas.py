"""Pydantic contracts for user and role administration."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.domain.identity.models import UserStatus


class RoleSummarySchema(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    is_system: bool


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=300)
    role_id: uuid.UUID
    preferred_language: str = Field(default="pl", min_length=2, max_length=10)


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=300)
    status: UserStatus | None = None
    role_id: uuid.UUID | None = None
    preferred_language: str | None = Field(None, min_length=2, max_length=10)
    bio: str | None = Field(None, max_length=5000)


class UserListItemSchema(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    status: UserStatus
    roles: list[str]
    primary_role: RoleSummarySchema | None
    created_at: datetime
    last_login_at: datetime | None


class UserListResponseSchema(BaseModel):
    items: list[UserListItemSchema]
    total: int
    page: int
    per_page: int
    pages: int


class PermissionSchema(BaseModel):
    key: str
    resource: str
    action: str
    description: str
    group: str
    assignable_to_custom_roles: bool


class RoleSchema(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    is_system: bool
    user_count: int
    permissions: list[str]
    created_at: datetime


class RoleListResponseSchema(BaseModel):
    items: list[RoleSchema]
    permissions: list[PermissionSchema]


class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z][a-z0-9_]+$")
    display_name: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(None, max_length=1000)
    permissions: set[str] = Field(default_factory=set, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip().lower()


class UpdateRoleRequest(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = Field(None, max_length=1000)
    permissions: set[str] | None = Field(None, max_length=100)
