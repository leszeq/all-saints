"""Image file upload and public object-storage read endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status

from src.domain.identity.models import User
from src.infrastructure.storage.avatar_storage import (
    MAX_AVATAR_BYTES,
    AvatarStorage,
    InvalidAvatarError,
    get_avatar_storage,
    prepare_avatar,
)
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.sources.schemas import ImageUploadSchema

router = APIRouter()


@router.post(
    "/images/upload",
    response_model=ImageUploadSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an avatar image",
    description="Validate, normalize and store a JPG, PNG or WebP file with a generated thumbnail.",
)
async def upload_avatar_image(
    request: Request,
    file: UploadFile = File(...),
    _user: User = Depends(require_permission("images", "create")),
    storage: AvatarStorage = Depends(get_avatar_storage),
) -> ImageUploadSchema:
    """Store an uploaded avatar and return URLs ready for a person payload."""
    content = await file.read(MAX_AVATAR_BYTES + 1)
    await file.close()
    try:
        prepared = await asyncio.to_thread(prepare_avatar, content, file.content_type)
        stored = await storage.store(prepared)
    except InvalidAvatarError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    url = str(request.url_for("get_uploaded_image", object_key=stored.storage_key))
    thumbnail_url = str(
        request.url_for(
            "get_uploaded_image",
            object_key=stored.thumbnail_storage_key,
        )
    )
    return ImageUploadSchema(
        url=url,
        thumbnail_url=thumbnail_url,
        storage_key=stored.storage_key,
        width_px=stored.width,
        height_px=stored.height,
        file_size_bytes=stored.file_size_bytes,
    )


@router.get(
    "/images/files/{object_key:path}",
    name="get_uploaded_image",
    response_class=Response,
    summary="Read an uploaded avatar image",
)
async def get_uploaded_image(
    object_key: str,
    storage: AvatarStorage = Depends(get_avatar_storage),
) -> Response:
    """Proxy a generated image from object storage with immutable caching."""
    try:
        content = await storage.read(object_key)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Obraz nie istnieje"
        ) from exc
    return Response(
        content=content,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
