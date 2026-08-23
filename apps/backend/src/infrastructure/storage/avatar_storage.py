"""Validated avatar processing and object-storage access."""

from __future__ import annotations

import asyncio
import io
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from PIL import Image, ImageOps, UnidentifiedImageError

from src.core.config import Settings, StorageBackend, settings

MAX_AVATAR_BYTES = 8 * 1024 * 1024
MAX_AVATAR_PIXELS = 40_000_000
MAX_AVATAR_EDGE = 2400
THUMBNAIL_EDGE = 512
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
STORAGE_KEY_PATTERN = re.compile(
    r"^avatars/\d{4}/\d{2}/[0-9a-f-]{36}(?:-thumbnail)?\.webp$"
)


class InvalidAvatarError(ValueError):
    """Raised when an uploaded file is not a safe supported image."""


@dataclass(frozen=True, slots=True)
class PreparedAvatar:
    """Normalized full-size avatar and its thumbnail."""

    content: bytes
    thumbnail: bytes
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class StoredAvatar:
    """Object keys and metadata returned after a successful upload."""

    storage_key: str
    thumbnail_storage_key: str
    width: int
    height: int
    file_size_bytes: int


def prepare_avatar(content: bytes, declared_content_type: str | None) -> PreparedAvatar:
    """Validate image bytes, orient them and encode two safe WebP variants."""
    if not content:
        raise InvalidAvatarError("Wybrany plik jest pusty")
    if len(content) > MAX_AVATAR_BYTES:
        raise InvalidAvatarError("Obraz może mieć maksymalnie 8 MB")
    if declared_content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidAvatarError("Dozwolone formaty to JPG, PNG i WebP")

    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in ALLOWED_FORMATS:
                raise InvalidAvatarError("Dozwolone formaty to JPG, PNG i WebP")
            if source.width * source.height > MAX_AVATAR_PIXELS:
                raise InvalidAvatarError("Obraz ma zbyt dużą rozdzielczość")
            source.load()
            image = ImageOps.exif_transpose(source)
            has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
        raise InvalidAvatarError("Plik nie jest prawidłowym obrazem") from exc

    image.thumbnail((MAX_AVATAR_EDGE, MAX_AVATAR_EDGE), Image.Resampling.LANCZOS)
    thumbnail = image.copy()
    thumbnail.thumbnail((THUMBNAIL_EDGE, THUMBNAIL_EDGE), Image.Resampling.LANCZOS)

    content_buffer = io.BytesIO()
    thumbnail_buffer = io.BytesIO()
    image.save(content_buffer, format="WEBP", quality=88, method=6)
    thumbnail.save(thumbnail_buffer, format="WEBP", quality=82, method=6)

    return PreparedAvatar(
        content=content_buffer.getvalue(),
        thumbnail=thumbnail_buffer.getvalue(),
        width=image.width,
        height=image.height,
    )


class AvatarStorage:
    """Store normalized avatars in MinIO, S3 or the local filesystem."""

    def __init__(self, app_settings: Settings) -> None:
        self.settings = app_settings
        self.bucket = (
            app_settings.AWS_S3_BUCKET
            if app_settings.STORAGE_BACKEND == StorageBackend.S3
            else app_settings.MINIO_BUCKET_IMAGES
        )
        self.local_root = app_settings.BASE_DIR / ".storage" / self.bucket
        self._client: BaseClient | None = None

    def _s3_client(self) -> BaseClient:
        if self._client is not None:
            return self._client

        kwargs = {
            "aws_access_key_id": self.settings.MINIO_ACCESS_KEY,
            "aws_secret_access_key": self.settings.MINIO_SECRET_KEY,
            "region_name": self.settings.AWS_REGION,
        }
        if self.settings.STORAGE_BACKEND == StorageBackend.MINIO:
            protocol = "https" if self.settings.MINIO_USE_SSL else "http"
            kwargs["endpoint_url"] = f"{protocol}://{self.settings.MINIO_ENDPOINT}"
        else:
            kwargs["aws_access_key_id"] = self.settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = self.settings.AWS_SECRET_ACCESS_KEY

        self._client = boto3.client("s3", **kwargs)
        return self._client

    def _ensure_minio_bucket(self) -> None:
        client = self._s3_client()
        try:
            client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            try:
                client.create_bucket(Bucket=self.bucket)
            except ClientError as create_exc:
                create_code = str(create_exc.response.get("Error", {}).get("Code", ""))
                if create_code not in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
                    raise

    @staticmethod
    def _validate_storage_key(storage_key: str) -> None:
        if not STORAGE_KEY_PATTERN.fullmatch(storage_key):
            raise FileNotFoundError(storage_key)

    def _write_local(self, storage_key: str, content: bytes) -> None:
        destination = self.local_root / storage_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    def _put_objects(self, storage_key: str, thumbnail_key: str, avatar: PreparedAvatar) -> None:
        if self.settings.STORAGE_BACKEND == StorageBackend.LOCAL:
            self._write_local(storage_key, avatar.content)
            self._write_local(thumbnail_key, avatar.thumbnail)
            return

        if self.settings.STORAGE_BACKEND == StorageBackend.MINIO:
            self._ensure_minio_bucket()
        client = self._s3_client()
        client.put_object(
            Bucket=self.bucket,
            Key=storage_key,
            Body=avatar.content,
            ContentType="image/webp",
            CacheControl="public, max-age=31536000, immutable",
        )
        client.put_object(
            Bucket=self.bucket,
            Key=thumbnail_key,
            Body=avatar.thumbnail,
            ContentType="image/webp",
            CacheControl="public, max-age=31536000, immutable",
        )

    async def store(self, avatar: PreparedAvatar) -> StoredAvatar:
        """Persist both variants and return their immutable storage keys."""
        now = datetime.now(UTC)
        image_id = uuid.uuid4()
        prefix = f"avatars/{now.year:04d}/{now.month:02d}/{image_id}"
        storage_key = f"{prefix}.webp"
        thumbnail_key = f"{prefix}-thumbnail.webp"
        await asyncio.to_thread(
            self._put_objects,
            storage_key,
            thumbnail_key,
            avatar,
        )
        return StoredAvatar(
            storage_key=storage_key,
            thumbnail_storage_key=thumbnail_key,
            width=avatar.width,
            height=avatar.height,
            file_size_bytes=len(avatar.content),
        )

    def _read_sync(self, storage_key: str) -> bytes:
        self._validate_storage_key(storage_key)
        if self.settings.STORAGE_BACKEND == StorageBackend.LOCAL:
            source = self.local_root / storage_key
            try:
                return source.read_bytes()
            except FileNotFoundError:
                raise

        try:
            response = self._s3_client().get_object(Bucket=self.bucket, Key=storage_key)
            return response["Body"].read()
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise FileNotFoundError(storage_key) from exc
            raise

    async def read(self, storage_key: str) -> bytes:
        """Read a generated avatar object without exposing storage credentials."""
        return await asyncio.to_thread(self._read_sync, storage_key)


@lru_cache(maxsize=1)
def get_avatar_storage() -> AvatarStorage:
    """Return the process-wide avatar storage adapter."""
    return AvatarStorage(settings)
