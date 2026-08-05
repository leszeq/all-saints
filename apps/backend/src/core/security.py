"""
Authentication & security services.

Provides:
- Password hashing (bcrypt)
- JWT access and refresh token generation/verification
- RBAC permission checking
- Security utilities (token revocation, brute-force protection)
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext

from src.core.config import settings


# ==============================================================================
# PASSWORD HASHING
# ==============================================================================


class PasswordHasher:
    """
    Secure password hashing using bcrypt via Passlib.

    Uses configurable cost factor from settings (recommended: 12).
    """

    def __init__(self) -> None:
        self._context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.BCRYPT_ROUNDS,
        )

    def hash(self, plain_password: str) -> str:
        """
        Hash a plain-text password.

        Args:
            plain_password: The password to hash.

        Returns:
            Bcrypt hash string.
        """
        return self._context.hash(plain_password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain-text password against a stored hash.

        Args:
            plain_password: Password provided by the user.
            hashed_password: Stored bcrypt hash.

        Returns:
            True if the password matches.
        """
        return self._context.verify(plain_password, hashed_password)

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if a hash needs to be rehashed (e.g. cost factor changed).

        Returns:
            True if the hash should be updated.
        """
        return self._context.needs_update(hashed_password)


# Singleton instance
password_hasher = PasswordHasher()


# ==============================================================================
# JWT TOKEN SERVICE
# ==============================================================================


class TokenPayload:
    """Parsed JWT token payload."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.sub: str = data.get("sub", "")          # User UUID
        self.type: str = data.get("type", "")         # "access" or "refresh"
        self.jti: str = data.get("jti", "")           # Token ID (for revocation)
        self.exp: int = data.get("exp", 0)
        self.iat: int = data.get("iat", 0)
        self.roles: list[str] = data.get("roles", [])
        self.email: str = data.get("email", "")

    @property
    def user_id(self) -> UUID:
        """Parse subject as UUID."""
        return UUID(self.sub)

    @property
    def is_expired(self) -> bool:
        """True if token has expired."""
        return datetime.now(timezone.utc).timestamp() > self.exp

    @property
    def is_access_token(self) -> bool:
        """True if this is an access token."""
        return self.type == "access"

    @property
    def is_refresh_token(self) -> bool:
        """True if this is a refresh token."""
        return self.type == "refresh"


class JWTService:
    """
    JWT token generation and verification service.

    Access tokens: short-lived (15 min), carries user identity + roles.
    Refresh tokens: long-lived (30 days), opaque string stored server-side.
    """

    def __init__(self) -> None:
        self._secret = settings.JWT_SECRET_KEY
        self._algorithm = settings.JWT_ALGORITHM
        self._access_ttl = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        self._refresh_ttl = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        roles: list[str],
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a signed JWT access token.

        Args:
            user_id: User's UUID.
            email: User's email address.
            roles: List of role names.
            extra_claims: Optional additional claims.

        Returns:
            Signed JWT string.
        """
        now = datetime.now(timezone.utc)
        jti = secrets.token_urlsafe(16)

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "roles": roles,
            "type": "access",
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int((now + self._access_ttl).timestamp()),
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(self) -> tuple[str, str]:
        """
        Create a refresh token.

        Returns:
            Tuple of (raw_token, token_hash).
            Store only the hash; return the raw token to the client.
        """
        raw_token = secrets.token_urlsafe(64)
        token_hash = self._hash_token(raw_token)
        return raw_token, token_hash

    def verify_access_token(self, token: str) -> TokenPayload:
        """
        Verify and decode an access token.

        Args:
            token: JWT string.

        Returns:
            Parsed TokenPayload.

        Raises:
            JWTError: If token is invalid or expired.
        """
        try:
            payload_data = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
            payload = TokenPayload(payload_data)

            if not payload.is_access_token:
                raise JWTError("Not an access token")

            return payload

        except JWTError as exc:
            logger.warning(f"JWT verification failed: {exc}")
            raise

    def get_token_expiry(self, token_type: str = "access") -> datetime:
        """Get expiry datetime for a token type."""
        now = datetime.now(timezone.utc)
        if token_type == "access":
            return now + self._access_ttl
        return now + self._refresh_ttl

    @staticmethod
    def _hash_token(token: str) -> str:
        """SHA-256 hash a refresh token for safe storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        """Public alias for token hashing."""
        return hashlib.sha256(token.encode()).hexdigest()


# Singleton instance
jwt_service = JWTService()


# ==============================================================================
# SECURITY UTILITIES
# ==============================================================================


def generate_verification_token() -> str:
    """Generate a secure email verification token."""
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    """Generate a secure password reset token."""
    return secrets.token_urlsafe(32)


def is_strong_password(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength.

    Rules:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Returns:
        Tuple of (is_valid, list_of_violated_rules).
    """
    errors: list[str] = []

    if len(password) < 8:
        errors.append("Hasło musi mieć co najmniej 8 znaków")
    if not any(c.isupper() for c in password):
        errors.append("Hasło musi zawierać co najmniej jedną wielką literę")
    if not any(c.islower() for c in password):
        errors.append("Hasło musi zawierać co najmniej jedną małą literę")
    if not any(c.isdigit() for c in password):
        errors.append("Hasło musi zawierać co najmniej jedną cyfrę")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Hasło musi zawierać co najmniej jeden znak specjalny")

    return len(errors) == 0, errors
