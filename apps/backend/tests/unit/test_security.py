"""
Unit tests for core security functions.
"""

from uuid import uuid4

from src.core.security import (
    JWTService,
    PasswordHasher,
    is_strong_password,
    jwt_service,
    password_hasher,
)


def test_password_hashing():
    password = "SecurePassword123!"
    hashed = password_hasher.hash(password)

    assert hashed != password
    assert password_hasher.verify(password, hashed) is True
    assert password_hasher.verify("WrongPassword123!", hashed) is False


def test_password_strength_validator():
    is_valid, errors = is_strong_password("SecurePassword123!")
    assert is_valid is True
    assert len(errors) == 0

    is_valid_weak, errors_weak = is_strong_password("weak")
    assert is_valid_weak is False
    assert len(errors_weak) > 0


def test_jwt_token_creation_and_verification():
    user_id = uuid4()
    email = "test@all-saints.local"
    roles = ["admin", "editor"]

    token = jwt_service.create_access_token(
        user_id=user_id,
        email=email,
        roles=roles,
    )

    assert isinstance(token, str)
    assert len(token) > 0

    payload = jwt_service.verify_access_token(token)
    assert payload.user_id == user_id
    assert payload.email == email
    assert payload.roles == roles
    assert payload.is_access_token is True


def test_refresh_token_generation_and_hashing():
    raw_token, token_hash = jwt_service.create_refresh_token()

    assert len(raw_token) > 30
    assert len(token_hash) == 64
    assert JWTService.hash_refresh_token(raw_token) == token_hash
