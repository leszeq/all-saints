"""
Sources & Media API router (Bibliography, Historical Sources, Images, Documents).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.hagiography.models import Person
from src.domain.identity.models import User
from src.domain.sources.models import (
    Bibliography,
    Document,
    HistoricalSource,
    Image,
    ImageLicense,
    PersonSource,
    SourceType,
)
from src.infrastructure.db.session import get_db_session
from src.infrastructure.storage.avatar_storage import (
    MAX_AVATAR_BYTES,
    AvatarStorage,
    InvalidAvatarError,
    get_avatar_storage,
    prepare_avatar,
)
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.sources.schemas import (
    BibliographyCreateSchema,
    BibliographySchema,
    DocumentCreateSchema,
    DocumentSchema,
    HistoricalSourceCreateSchema,
    HistoricalSourceSchema,
    ImageCreateSchema,
    ImageSchema,
    ImageUploadSchema,
    PersonSourceCreateSchema,
    PersonSourceSchema,
    PersonWebSourceCreateSchema,
)

router = APIRouter()


# ==============================================================================
# BIBLIOGRAPHY
# ==============================================================================


@router.get("/bibliography", response_model=list[BibliographySchema], summary="List bibliography entries")
async def list_bibliography(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[BibliographySchema]:
    query = select(Bibliography).where(Bibliography.deleted_at.is_(None))
    if search:
        query = query.where(Bibliography.title.ilike(f"%{search}%") | Bibliography.authors.ilike(f"%{search}%"))
    query = query.order_by(Bibliography.year.desc().nullslast(), Bibliography.title.asc()).limit(100)
    res = await db.execute(query)
    return [BibliographySchema.model_validate(b) for b in res.scalars().all()]


@router.post("/bibliography", response_model=BibliographySchema, status_code=status.HTTP_201_CREATED, summary="Create bibliography entry")
async def create_bibliography(
    data: BibliographyCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> BibliographySchema:
    bib = Bibliography(**data.model_dump())
    db.add(bib)
    await db.commit()
    await db.refresh(bib)
    return BibliographySchema.model_validate(bib)


# ==============================================================================
# HISTORICAL SOURCES
# ==============================================================================


@router.get("/historical-sources", response_model=list[HistoricalSourceSchema], summary="List primary historical sources")
async def list_historical_sources(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[HistoricalSourceSchema]:
    query = select(HistoricalSource).where(HistoricalSource.deleted_at.is_(None))
    if search:
        query = query.where(HistoricalSource.title.ilike(f"%{search}%") | HistoricalSource.repository.ilike(f"%{search}%"))
    query = query.order_by(HistoricalSource.title.asc()).limit(100)
    res = await db.execute(query)
    return [HistoricalSourceSchema.model_validate(s) for s in res.scalars().all()]


@router.post("/historical-sources", response_model=HistoricalSourceSchema, status_code=status.HTTP_201_CREATED, summary="Create historical source")
async def create_historical_source(
    data: HistoricalSourceCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> HistoricalSourceSchema:
    src = HistoricalSource(**data.model_dump())
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return HistoricalSourceSchema.model_validate(src)


# ==============================================================================
# PERSON SOURCE LINKS
# ==============================================================================


@router.get(
    "/person-links/{person_id}",
    response_model=list[PersonSourceSchema],
    summary="List sources assigned to a person",
)
async def list_person_sources(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "read")),
) -> list[PersonSourceSchema]:
    """Return active bibliography and historical-source assignments."""
    result = await db.execute(
        select(PersonSource)
        .options(
            selectinload(PersonSource.bibliography),
            selectinload(PersonSource.historical_source),
        )
        .where(
            PersonSource.person_id == person_id,
            PersonSource.deleted_at.is_(None),
            or_(
                PersonSource.bibliography.has(Bibliography.deleted_at.is_(None)),
                PersonSource.historical_source.has(HistoricalSource.deleted_at.is_(None)),
            ),
        )
        .order_by(PersonSource.is_primary.desc(), PersonSource.created_at.asc())
    )
    return [PersonSourceSchema.model_validate(link) for link in result.scalars().all()]


@router.post(
    "/person-links/{person_id}",
    response_model=PersonSourceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a source to a person",
)
async def create_person_source(
    person_id: uuid.UUID,
    data: PersonSourceCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> PersonSourceSchema:
    """Create a non-duplicated source assignment used by data-quality scoring."""
    person = (
        await db.execute(
            select(Person).where(Person.id == person_id, Person.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Osoba nie istnieje")

    source_model = Bibliography if data.bibliography_id is not None else HistoricalSource
    source_id = data.bibliography_id or data.historical_source_id
    source = (
        await db.execute(
            select(source_model).where(
                source_model.id == source_id,
                source_model.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Źródło nie istnieje")

    source_field = (
        PersonSource.bibliography_id
        if data.bibliography_id is not None
        else PersonSource.historical_source_id
    )
    existing = (
        await db.execute(
            select(PersonSource).where(
                PersonSource.person_id == person_id,
                source_field == source_id,
                PersonSource.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="To źródło jest już przypisane do postaci",
        )

    link = PersonSource(person_id=person_id, **data.model_dump())
    db.add(link)
    await db.commit()

    result = await db.execute(
        select(PersonSource)
        .options(
            selectinload(PersonSource.bibliography),
            selectinload(PersonSource.historical_source),
        )
        .where(PersonSource.id == link.id)
    )
    return PersonSourceSchema.model_validate(result.scalar_one())


@router.post(
    "/person-links/{person_id}/web",
    response_model=PersonSourceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create and assign a website source to a person",
)
async def create_person_web_source(
    person_id: uuid.UUID,
    data: PersonWebSourceCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> PersonSourceSchema:
    """Create or reuse a URL source and attach it in one transaction."""
    person = (
        await db.execute(
            select(Person).where(Person.id == person_id, Person.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Osoba nie istnieje")

    normalized_url = str(data.url)
    bibliography = (
        await db.execute(
            select(Bibliography).where(
                Bibliography.url == normalized_url,
                Bibliography.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if bibliography is None:
        bibliography = Bibliography(
            source_type=SourceType.WEBSITE,
            title=data.title,
            url=normalized_url,
            authors=data.authors,
            publisher=data.publisher,
            year=data.year,
            language=data.language,
            reliability_score=data.reliability_score,
        )
        db.add(bibliography)
        await db.flush()

    existing = (
        await db.execute(
            select(PersonSource).where(
                PersonSource.person_id == person_id,
                PersonSource.bibliography_id == bibliography.id,
                PersonSource.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ten link jest już przypisany do postaci",
        )

    link = PersonSource(
        person_id=person_id,
        bibliography_id=bibliography.id,
        page_reference=data.page_reference,
        relevance_score=data.relevance_score,
        is_primary=data.is_primary,
        notes=data.notes,
    )
    db.add(link)
    await db.commit()

    result = await db.execute(
        select(PersonSource)
        .options(
            selectinload(PersonSource.bibliography),
            selectinload(PersonSource.historical_source),
        )
        .where(PersonSource.id == link.id)
    )
    return PersonSourceSchema.model_validate(result.scalar_one())


@router.delete(
    "/person-links/{person_id}/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Remove a source assignment from a person",
)
async def delete_person_source(
    person_id: uuid.UUID,
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "delete")),
) -> None:
    """Soft-delete one source assignment without deleting the source itself."""
    link = (
        await db.execute(
            select(PersonSource).where(
                PersonSource.id == link_id,
                PersonSource.person_id == person_id,
                PersonSource.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Przypisanie źródła nie istnieje",
        )
    link.deleted_at = datetime.now(UTC)
    await db.commit()


# ==============================================================================
# IMAGES
# ==============================================================================


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obraz nie istnieje") from exc
    return Response(
        content=content,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/images", response_model=list[ImageSchema], summary="List images")
async def list_images(
    person_id: uuid.UUID | None = None,
    license: ImageLicense | None = Query(None),
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[ImageSchema]:
    query = select(Image).where(Image.deleted_at.is_(None))
    if person_id:
        query = query.where(Image.person_id == person_id)
    if license is not None:
        query = query.where(Image.license == license.value)
    query = query.order_by(Image.is_primary.desc(), Image.sort_order.asc()).limit(limit)
    res = await db.execute(query)
    return [ImageSchema.model_validate(i) for i in res.scalars().all()]


@router.post("/images", response_model=ImageSchema, status_code=status.HTTP_201_CREATED, summary="Create image record")
async def create_image(
    data: ImageCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("images", "create")),
) -> ImageSchema:
    if data.person_id is not None and data.is_primary:
        await db.execute(
            update(Image)
            .where(
                Image.person_id == data.person_id,
                Image.deleted_at.is_(None),
                Image.is_primary.is_(True),
            )
            .values(is_primary=False)
        )
    img = Image(**data.model_dump())
    db.add(img)
    await db.commit()
    await db.refresh(img)
    return ImageSchema.model_validate(img)


# ==============================================================================
# DOCUMENTS
# ==============================================================================


@router.get("/documents", response_model=list[DocumentSchema], summary="List documents")
async def list_documents(
    person_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[DocumentSchema]:
    query = select(Document).where(Document.deleted_at.is_(None))
    if person_id:
        query = query.where(Document.person_id == person_id)
    query = query.order_by(Document.created_at.desc()).limit(100)
    res = await db.execute(query)
    return [DocumentSchema.model_validate(d) for d in res.scalars().all()]


@router.post("/documents", response_model=DocumentSchema, status_code=status.HTTP_201_CREATED, summary="Create document record")
async def create_document(
    data: DocumentCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> DocumentSchema:
    doc = Document(**data.model_dump())
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return DocumentSchema.model_validate(doc)
