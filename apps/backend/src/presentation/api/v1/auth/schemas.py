"""Transport schemas for authentication and the current-user account."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Login credentials."""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=1, description="Password")


class TokenResponse(BaseModel):
    """Successful authentication response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class UserProfileResponse(BaseModel):
    """Current user profile."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    status: str
    roles: list[str]
    permissions: list[str]
    preferred_language: str
    last_login_at: datetime | None


class ChangePasswordRequest(BaseModel):
    """Password change request."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class UpdateProfileRequest(BaseModel):
    """Editable fields of the current user's profile."""

    full_name: str | None = Field(None, min_length=2, max_length=300)
    preferred_language: str | None = Field(None, min_length=2, max_length=10)
