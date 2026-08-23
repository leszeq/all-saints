"""Tests for validated avatar processing and local storage."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from src.core.config import StorageBackend, settings
from src.infrastructure.storage.avatar_storage import (
    AvatarStorage,
    InvalidAvatarError,
    prepare_avatar,
)


def _png_bytes(width: int = 1200, height: int = 800) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=(94, 32, 49)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_prepare_avatar_creates_webp_and_thumbnail() -> None:
    prepared = prepare_avatar(_png_bytes(), "image/png")

    assert (prepared.width, prepared.height) == (1200, 800)
    with Image.open(io.BytesIO(prepared.content)) as full_image:
        assert full_image.format == "WEBP"
        assert full_image.size == (1200, 800)
    with Image.open(io.BytesIO(prepared.thumbnail)) as thumbnail:
        assert thumbnail.format == "WEBP"
        assert max(thumbnail.size) == 512


def test_prepare_avatar_rejects_spoofed_file() -> None:
    with pytest.raises(InvalidAvatarError, match="prawidłowym obrazem"):
        prepare_avatar(b"not an image", "image/png")


def test_prepare_avatar_rejects_unsupported_content_type() -> None:
    with pytest.raises(InvalidAvatarError, match="JPG"):
        prepare_avatar(_png_bytes(), "image/svg+xml")


@pytest.mark.asyncio
async def test_local_avatar_storage_round_trip(tmp_path) -> None:
    local_settings = settings.model_copy(
        update={
            "STORAGE_BACKEND": StorageBackend.LOCAL,
            "BASE_DIR": tmp_path,
        }
    )
    storage = AvatarStorage(local_settings)
    prepared = prepare_avatar(_png_bytes(320, 480), "image/png")

    stored = await storage.store(prepared)

    assert await storage.read(stored.storage_key) == prepared.content
    assert await storage.read(stored.thumbnail_storage_key) == prepared.thumbnail
    assert stored.width == 320
    assert stored.height == 480


@pytest.mark.asyncio
async def test_storage_rejects_unknown_key(tmp_path) -> None:
    local_settings = settings.model_copy(
        update={
            "STORAGE_BACKEND": StorageBackend.LOCAL,
            "BASE_DIR": tmp_path,
        }
    )
    storage = AvatarStorage(local_settings)

    with pytest.raises(FileNotFoundError):
        await storage.read("../../secrets.txt")
