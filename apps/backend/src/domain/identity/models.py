"""
Identity & Access Management domain models.

Covers: User, Role, Permission, UserRole, RolePermission,
        AuditLog, RefreshToken.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, MappedColumn, mapped_column, relationship

from src.domain.base import Base, BaseModel

if TYPE_CHECKING:
    pass


# ==============================================================================
# ENUMS
# ==============================================================================


class UserStatus(StrEnum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    PENDING_VERIFICATION = "pending_verification"


class SystemRole(StrEnum):
    """Predefined system roles (cannot be deleted)."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    TRANSLATOR = "translator"
    READER = "reader"
    GUEST = "guest"


class AuditAction(StrEnum):
    """Types of audited actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    EXPORT = "export"
    IMPORT = "import"
    PUBLISH = "publish"
    UNPUBLISH = "unpublish"


# ==============================================================================
# PERMISSION
# ==============================================================================


class Permission(BaseModel, Base):
    """
    Granular permission defining access to a resource and action.

    Example: resource="persons", action="create"
    """

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permission_resource_action"),
        Index("ix_permissions_resource", "resource"),
        {"comment": "Granular RBAC permissions"},
    )

    resource: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Resource name (e.g. 'persons', 'sources')",
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Action name (e.g. 'create', 'read', 'update', 'delete')",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    roles: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="permission", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Permission {self.resource}:{self.action}>"


# ==============================================================================
# ROLE
# ==============================================================================


class Role(BaseModel, Base):
    """
    User role grouping a set of permissions.

    System roles (is_system=True) cannot be deleted.
    """

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("name", name="uq_role_name"),
        {"comment": "RBAC roles"},
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Role identifier (e.g. 'super_admin', 'editor')",
    )
    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable role name",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="If True, this role cannot be deleted",
    )

    # Relationships
    permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", lazy="selectin"
    )
    users: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", lazy="selectin"
    )

    def has_permission(self, resource: str, action: str) -> bool:
        """Check if this role includes a specific permission."""
        return any(
            rp.permission.resource == resource and rp.permission.action == action
            for rp in self.permissions
            if rp.permission is not None
        )


# ==============================================================================
# ROLE <-> PERMISSION (association)
# ==============================================================================


class RolePermission(Base):
    """Many-to-many association: Role ↔ Permission."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        {"comment": "Role to permission assignments"},
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="permissions")
    permission: Mapped["Permission"] = relationship(
        "Permission", back_populates="roles"
    )


# ==============================================================================
# USER
# ==============================================================================


class User(BaseModel, Base):
    """
    System user (administrator, editor, translator, etc.).

    Passwords are stored as bcrypt hashes – never in plaintext.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_email"),
        Index("ix_users_email", "email"),
        Index("ix_users_status", "status"),
        {"comment": "Application users"},
    )

    # Core fields
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        comment="Unique email address",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password",
    )
    full_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        String(30),
        nullable=False,
        default=UserStatus.PENDING_VERIFICATION,
    )

    # Profile
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="pl",
    )

    # Security
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    two_factor_secret: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        foreign_keys="UserRole.user_id",
        back_populates="user",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", lazy="dynamic"
    )

    @property
    def is_active(self) -> bool:
        """True if account is active and not locked."""
        return self.status == UserStatus.ACTIVE

    @property
    def is_locked(self) -> bool:
        """True if account is temporarily locked due to failed login attempts."""
        from datetime import datetime, timezone
        return (
            self.locked_until is not None
            and self.locked_until > datetime.now(timezone.utc)
        )

    def get_permissions(self) -> set[str]:
        """Return all permission strings for this user (resource:action)."""
        perms: set[str] = set()
        for user_role in self.roles:
            if user_role.role:
                for rp in user_role.role.permissions:
                    if rp.permission:
                        perms.add(f"{rp.permission.resource}:{rp.permission.action}")
        return perms

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(ur.role.name == role_name for ur in self.roles if ur.role)

    def has_permission(self, resource: str, action: str) -> bool:
        """Check if user has a specific permission via any of their roles."""
        return f"{resource}:{action}" in self.get_permissions()


# ==============================================================================
# USER <-> ROLE (association)
# ==============================================================================


class UserRole(Base):
    """Many-to-many association: User ↔ Role."""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        {"comment": "User to role assignments"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    assigned_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="roles")
    role: Mapped["Role"] = relationship("Role", back_populates="users")


# ==============================================================================
# REFRESH TOKEN
# ==============================================================================


class RefreshToken(BaseModel, Base):
    """
    JWT refresh token storage.

    Stored hashed in the database. Each user can have multiple
    active refresh tokens (multiple devices/sessions).
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_token_hash", "token_hash"),
        {"comment": "JWT refresh token registry"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="SHA-256 hash of the refresh token",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(
        INET, nullable=True, comment="Client IP address"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        """True if token is not revoked and not expired."""
        from datetime import datetime, timezone
        return (
            self.revoked_at is None
            and self.expires_at > datetime.now(timezone.utc)
        )


# ==============================================================================
# AUDIT LOG
# ==============================================================================


class AuditLog(Base):
    """
    Immutable audit trail for all data-modifying operations.

    Records WHO did WHAT to WHICH record, with full before/after snapshots.
    Audit logs are never soft-deleted.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        {"comment": "Immutable audit trail"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Who
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL for system-generated events",
    )
    user_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        comment="Denormalized for historical accuracy",
    )

    # What
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="AuditAction enum value",
    )

    # Which resource
    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Table/entity name (e.g. 'persons')",
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Primary key of the affected record",
    )

    # Data snapshots
    old_value: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Record state BEFORE the change",
    )
    new_value: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Record state AFTER the change",
    )

    # Request context
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="Correlation ID from HTTP request",
    )

    # Additional metadata
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Additional context (e.g. export format, import filename)",
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")
