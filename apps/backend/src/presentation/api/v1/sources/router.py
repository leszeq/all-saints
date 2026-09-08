"""
Sources & Media API router (Bibliography, Historical Sources, Images, Documents).
"""

from __future__ import annotations

import asyncio
import uuid
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
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.audit_service import add_audit_log
from src.application.services.person_snapshot import (
    append_relation_version,
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.domain.hagiography.models import Person, PublicationStatus
from src.domain.identity.models import AuditAction, User
from src.domain.sources.models import (
    Bibliography,
    Document,
    HistoricalSource,
    Image,
    ImageLicense,
    PersonSource,
)
from src.infrastructure.db.session import get_db_session
from src.infrastructure.storage.avatar_storage import (
    MAX_AVATAR_BYTES,
    AvatarStorage,
    InvalidAvatarError,
    get_avatar_storage,
    prepare_avatar,
)
from src.presentation.api.pagination import (
    PAGINATION_RESPONSE_DOCS,
    PageNumber,
    PageSize,
    add_pagination_headers,
    execute_page,
)
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.sources.person_links import router as person_links_router
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
    SourceStatsSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()


# ==============================================================================
# BIBLIOGRAPHY
# ==============================================================================


@router.get("/stats", response_model=SourceStatsSchema, summary="Get public source statistics")
async def get_source_stats(
    db: AsyncSession = Depends(get_db_session),
) -> SourceStatsSchema:
    published_person_filter = (
        Person.deleted_at.is_(None),
        Person.status == PublicationStatus.PUBLISHED.value,
    )
    active_person_source_filter = (
        PersonSource.deleted_at.is_(None),
        or_(
            and_(
                PersonSource.bibliography_id.is_not(None),
                PersonSource.bibliography.has(Bibliography.deleted_at.is_(None)),
            ),
            and_(
                PersonSource.historical_source_id.is_not(None),
                PersonSource.historical_source.has(HistoricalSource.deleted_at.is_(None)),
            ),
        ),
    )

    total_published_persons = (
        await db.execute(select(func.count(Person.id)).where(*published_person_filter))
    ).scalar_one()
    documented_persons = (
        await db.execute(
            select(func.count(func.distinct(PersonSource.person_id)))
            .join(Person, Person.id == PersonSource.person_id)
            .where(*published_person_filter, *active_person_source_filter)
        )
    ).scalar_one()
    person_source_links = (
        await db.execute(
            select(func.count(PersonSource.id))
            .join(Person, Person.id == PersonSource.person_id)
            .where(*published_person_filter, *active_person_source_filter)
        )
    ).scalar_one()
    bibliography_sources = (
        await db.execute(
            select(func.count(Bibliography.id)).where(Bibliography.deleted_at.is_(None))
        )
    ).scalar_one()
    historical_sources = (
        await db.execute(
            select(func.count(HistoricalSource.id)).where(HistoricalSource.deleted_at.is_(None))
        )
    ).scalar_one()
    images = (
        await db.execute(
            select(func.count(Image.id))
            .join(Person, Person.id == Image.person_id)
            .where(*published_person_filter, Image.deleted_at.is_(None))
        )
    ).scalar_one()
    unknown_license_images = (
        await db.execute(
            select(func.count(Image.id))
            .join(Person, Person.id == Image.person_id)
            .where(
                *published_person_filter,
                Image.deleted_at.is_(None),
                Image.license == ImageLicense.UNKNOWN.value,
            )
        )
    ).scalar_one()

    return SourceStatsSchema(
        bibliography_sources=bibliography_sources,
        historical_sources=historical_sources,
        person_source_links=person_source_links,
        documented_persons=documented_persons,
        total_published_persons=total_published_persons,
        images=images,
        unknown_license_images=unknown_license_images,
    )


@router.get(
    "/bibliography",
    response_model=list[BibliographySchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List bibliography entries",
)
async def list_bibliography(
    response: Response,
    search: str | None = Query(None, max_length=100),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[BibliographySchema]:
    query = select(Bibliography).where(Bibliography.deleted_at.is_(None))
    if search:
        query = query.where(
            Bibliography.title.ilike(f"%{search}%") | Bibliography.authors.ilike(f"%{search}%")
        )
    query = query.order_by(Bibliography.year.desc().nullslast(), Bibliography.title.asc())
    items, total = await execute_page(db, query, page=page, per_page=per_page)
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [BibliographySchema.model_validate(item) for item in items]


@router.post(
    "/bibliography",
    response_model=BibliographySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create bibliography entry",
)
async def create_bibliography(
    data: BibliographyCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> BibliographySchema:
    bib = Bibliography(**data.model_dump())
    db.add(bib)
    await db.flush()
    await db.refresh(bib)
    return BibliographySchema.model_validate(bib)


# ==============================================================================
# HISTORICAL SOURCES
# ==============================================================================


@router.get(
    "/historical-sources",
    response_model=list[HistoricalSourceSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List primary historical sources",
)
async def list_historical_sources(
    response: Response,
    search: str | None = Query(None, max_length=100),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[HistoricalSourceSchema]:
    query = select(HistoricalSource).where(HistoricalSource.deleted_at.is_(None))
    if search:
        query = query.where(
            HistoricalSource.title.ilike(f"%{search}%")
            | HistoricalSource.repository.ilike(f"%{search}%")
        )
    query = query.order_by(HistoricalSource.title.asc())
    items, total = await execute_page(db, query, page=page, per_page=per_page)
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [HistoricalSourceSchema.model_validate(item) for item in items]


@router.post(
    "/historical-sources",
    response_model=HistoricalSourceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create historical source",
)
async def create_historical_source(
    data: HistoricalSourceCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> HistoricalSourceSchema:
    src = HistoricalSource(**data.model_dump())
    db.add(src)
    await db.flush()
    await db.refresh(src)
    return HistoricalSourceSchema.model_validate(src)


router.include_router(person_links_router)


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


@router.get(
    "/images",
    response_model=list[ImageSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List images",
)
async def list_images(
    response: Response,
    person_id: uuid.UUID | None = None,
    license: ImageLicense | None = Query(None),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    limit: Annotated[int | None, Query(ge=1, le=500, deprecated=True)] = None,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("images", "read")),
) -> list[ImageSchema]:
    query = select(Image).where(Image.deleted_at.is_(None))
    if person_id:
        query = query.where(Image.person_id == person_id)
    if license is not None:
        query = query.where(Image.license == license.value)
    query = query.order_by(Image.is_primary.desc(), Image.sort_order.asc())
    effective_per_page = limit if limit is not None else per_page
    items, total = await execute_page(db, query, page=page, per_page=effective_per_page)
    add_pagination_headers(
        response,
        total=total,
        page=page,
        per_page=effective_per_page,
    )
    return [ImageSchema.model_validate(item) for item in items]


@router.post(
    "/images",
    response_model=ImageSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create image record",
)
async def create_image(
    data: ImageCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("images", "create")),
) -> ImageSchema:
    person = None
    previous_snapshot = None
    if data.person_id is not None:
        person = await lock_person_for_snapshot(db, data.person_id)
        if person is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Osoba nie istnieje")
        previous_snapshot = await serialize_person_snapshot(db, person)
        if data.is_primary:
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
    if person is not None and previous_snapshot is not None:
        await db.flush()
        previous_snapshot, current_snapshot = await append_relation_version(
            db,
            person,
            previous_snapshot=previous_snapshot,
            changed_by_id=current_user.id,
            change_summary="Dodanie obrazu",
        )
        add_audit_log(
            db,
            context=audit_context_from_request(request, current_user),
            action=AuditAction.UPDATE,
            resource_type="persons",
            resource_id=person.id,
            old_value=previous_snapshot,
            new_value=current_snapshot,
            extra_metadata={"relation": "images", "operation": "add"},
        )
    await db.flush()
    await db.refresh(img)
    return ImageSchema.model_validate(img)


# ==============================================================================
# DOCUMENTS
# ==============================================================================


@router.get(
    "/documents",
    response_model=list[DocumentSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List documents",
)
async def list_documents(
    response: Response,
    person_id: uuid.UUID | None = None,
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "read")),
) -> list[DocumentSchema]:
    query = select(Document).where(Document.deleted_at.is_(None))
    if person_id:
        query = query.where(Document.person_id == person_id)
    query = query.order_by(Document.created_at.desc())
    items, total = await execute_page(db, query, page=page, per_page=per_page)
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [DocumentSchema.model_validate(item) for item in items]


@router.post(
    "/documents",
    response_model=DocumentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create document record",
)
async def create_document(
    data: DocumentCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> DocumentSchema:
    doc = Document(**data.model_dump())
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return DocumentSchema.model_validate(doc)
