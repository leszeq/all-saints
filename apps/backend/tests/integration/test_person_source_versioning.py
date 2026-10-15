"""Integration coverage for source-relation versioning through the HTTP API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.commands.person_sources import CreatePersonWebSourceCommand
from src.application.services.person_source_service import (
    PersonSourceConflictError,
    PersonSourceService,
)
from src.core.security import jwt_service
from src.domain.hagiography.models import (
    Gender,
    Person,
    PersonType,
    PersonVersion,
    PublicationStatus,
)
from src.domain.identity.models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserStatus,
)
from src.domain.sources.models import Bibliography, Document, PersonSource
from src.infrastructure.db.session import get_db_session
from src.main import app


async def _source_editor(
    db: AsyncSession,
    *,
    role_name: str = "source-version-editor",
    email: str = "source-version@example.com",
) -> tuple[User, dict[str, str]]:
    role = Role(name=role_name, display_name="Redaktor źródeł")
    db.add(role)
    await db.flush()
    for resource, action in (
        ("sources", "create"),
        ("sources", "delete"),
        ("images", "create"),
    ):
        permission = Permission(resource=resource, action=action)
        db.add(permission)
        await db.flush()
        db.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                granted_at=datetime.now(UTC),
            )
        )
    user = User(
        email=email,
        hashed_password="not-used-by-token-tests",
        full_name="Redaktor Źródeł",
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    db.add(
        UserRole(
            user_id=user.id,
            role_id=role.id,
            assigned_at=datetime.now(UTC),
            assigned_by_id=None,
        )
    )
    await db.commit()
    token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=[role.name],
    )
    return user, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_source_relation_waits_for_request_unit_of_work(
    test_engine,
    db_session: AsyncSession,
) -> None:
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    user, headers = await _source_editor(
        db_session,
        role_name="source-transaction-editor",
        email="source-transaction@example.com",
    )
    person = Person(
        slug="sw-zrodlo-oczekujace-na-commit",
        canonical_name="Św. Źródło Oczekujące na Commit",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
        version=1,
    )
    bibliography = Bibliography(title="Źródło oczekujące na commit")
    db_session.add_all([person, bibliography])
    await db_session.commit()
    person_id = person.id
    bibliography_id = bibliography.id
    user_id = user.id

    async with session_factory() as writer_session, session_factory() as observer_session:

        async def override_get_db_without_commit():
            yield writer_session

        app.dependency_overrides[get_db_session] = override_get_db_without_commit
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",
            ) as client:
                response = await client.post(
                    f"/api/v1/sources/person-links/{person_id}",
                    headers=headers,
                    json={"bibliography_id": str(bibliography_id), "is_primary": True},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        link_id = uuid.UUID(response.json()["id"])
        observed_person = (
            await observer_session.execute(select(Person).where(Person.id == person_id))
        ).scalar_one()
        observed_link = (
            await observer_session.execute(select(PersonSource).where(PersonSource.id == link_id))
        ).scalar_one_or_none()
        observed_versions = (
            (
                await observer_session.execute(
                    select(PersonVersion).where(PersonVersion.person_id == person_id)
                )
            )
            .scalars()
            .all()
        )
        observed_audit = (
            (
                await observer_session.execute(
                    select(AuditLog).where(
                        AuditLog.resource_id == person_id,
                        AuditLog.user_id == user_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert observed_person.version == 1
        assert observed_link is None
        assert observed_versions == []
        assert observed_audit == []

        await writer_session.commit()
        await observer_session.refresh(observed_person)
        committed_link = (
            await observer_session.execute(select(PersonSource).where(PersonSource.id == link_id))
        ).scalar_one()
        committed_version = (
            await observer_session.execute(
                select(PersonVersion).where(
                    PersonVersion.person_id == person_id,
                    PersonVersion.version_number == 2,
                )
            )
        ).scalar_one()
        committed_audit = (
            await observer_session.execute(
                select(AuditLog).where(
                    AuditLog.resource_id == person_id,
                    AuditLog.user_id == user_id,
                )
            )
        ).scalar_one()
        assert observed_person.version == 2
        assert committed_link.bibliography_id == bibliography_id
        assert committed_version.snapshot["sources"][0]["bibliography_id"] == str(bibliography_id)
        assert committed_audit.extra_metadata["relation"] == "sources"


@pytest.mark.asyncio
async def test_adding_and_removing_source_creates_person_versions(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user, headers = await _source_editor(db_session)
    person = Person(
        slug="sw-zrodlo-wersjonowane",
        canonical_name="Św. Źródło Wersjonowane",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
        version=1,
    )
    bibliography = Bibliography(title="Wersjonowane źródło")
    db_session.add_all([person, bibliography])
    await db_session.commit()

    create_response = await async_client.post(
        f"/api/v1/sources/person-links/{person.id}",
        headers=headers,
        json={
            "bibliography_id": str(bibliography.id),
            "page_reference": "s. 42",
            "is_primary": True,
        },
    )

    assert create_response.status_code == 201
    link_id = create_response.json()["id"]
    await db_session.refresh(person)
    assert person.version == 2
    created_version = (
        await db_session.execute(
            select(PersonVersion).where(
                PersonVersion.person_id == person.id,
                PersonVersion.version_number == 2,
            )
        )
    ).scalar_one()
    assert created_version.changed_by_id == user.id
    assert created_version.snapshot["sources"][0]["bibliography_id"] == str(bibliography.id)

    delete_response = await async_client.delete(
        f"/api/v1/sources/person-links/{person.id}/{link_id}",
        headers=headers,
    )

    assert delete_response.status_code == 204
    await db_session.refresh(person)
    assert person.version == 3
    removed_version = (
        await db_session.execute(
            select(PersonVersion).where(
                PersonVersion.person_id == person.id,
                PersonVersion.version_number == 3,
            )
        )
    ).scalar_one()
    assert removed_version.snapshot["sources"] == []

    image_response = await async_client.post(
        "/api/v1/sources/images",
        headers=headers,
        json={
            "person_id": str(person.id),
            "url": "https://example.test/versioned-image.jpg",
            "is_primary": True,
        },
    )

    assert image_response.status_code == 201
    await db_session.refresh(person)
    assert person.version == 4
    image_version = (
        await db_session.execute(
            select(PersonVersion).where(
                PersonVersion.person_id == person.id,
                PersonVersion.version_number == 4,
            )
        )
    ).scalar_one()
    assert image_version.snapshot["images"][0]["url"] == (
        "https://example.test/versioned-image.jpg"
    )
    audit_events = list(
        (
            await db_session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == person.id)
                .order_by(AuditLog.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    assert [event.extra_metadata["operation"] for event in audit_events] == [
        "add",
        "remove",
        "add",
    ]


@pytest.mark.asyncio
async def test_published_relation_mutations_require_publish_permission(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _user, headers = await _source_editor(
        db_session,
        role_name="published-relation-editor",
        email="published-relation@example.com",
    )
    person = Person(
        slug="sw-zrodlo-opublikowane",
        canonical_name="Św. Źródło Opublikowane",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.UNKNOWN.value,
    )
    bibliography = Bibliography(title="Źródło opublikowanej postaci")
    db_session.add_all([person, bibliography])
    await db_session.flush()
    person_id = person.id
    bibliography_id = bibliography.id
    await db_session.commit()

    source_response = await async_client.post(
        f"/api/v1/sources/person-links/{person_id}",
        headers=headers,
        json={"bibliography_id": str(bibliography_id)},
    )
    image_response = await async_client.post(
        "/api/v1/sources/images",
        headers=headers,
        json={
            "person_id": str(person_id),
            "url": "https://example.test/published-image.jpg",
        },
    )

    assert source_response.status_code == 403
    assert image_response.status_code == 403
    assert "persons:publish" in source_response.json()["detail"]


@pytest.mark.asyncio
async def test_image_metadata_rejects_missing_person(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _user, headers = await _source_editor(
        db_session,
        role_name="missing-image-person-editor",
        email="missing-image-person@example.com",
    )

    response = await async_client.post(
        "/api/v1/sources/images",
        headers=headers,
        json={
            "person_id": str(uuid.uuid4()),
            "url": "https://example.test/missing-person.jpg",
            "is_primary": True,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Osoba nie istnieje"


@pytest.mark.asyncio
async def test_document_metadata_is_created_through_application_service(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _user, headers = await _source_editor(
        db_session,
        role_name="document-metadata-editor",
        email="document-metadata@example.com",
    )

    response = await async_client.post(
        "/api/v1/sources/documents",
        headers=headers,
        json={
            "title": "Dekret o heroiczności cnót",
            "document_type": "decree",
            "language_code": "la",
            "file_url": "https://example.test/decree.pdf",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    document = await db_session.get(Document, uuid.UUID(payload["id"]))
    assert document is not None
    assert document.title == "Dekret o heroiczności cnót"
    assert document.document_type == "decree"


@pytest.mark.asyncio
async def test_web_source_is_reused_and_duplicate_assignment_is_rejected(
    db_session: AsyncSession,
) -> None:
    first_person = Person(
        slug="sw-pierwsze-zrodlo-internetowe",
        canonical_name="Św. Pierwsze Źródło Internetowe",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
        version=1,
    )
    second_person = Person(
        slug="sw-drugie-zrodlo-internetowe",
        canonical_name="Św. Drugie Źródło Internetowe",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
        version=1,
    )
    db_session.add_all([first_person, second_person])
    await db_session.flush()

    service = PersonSourceService(db_session)
    source = CreatePersonWebSourceCommand(
        title="Wspólny oficjalny biogram",
        url="https://example.test/shared-biography",
        is_primary=True,
    )

    first_link = await service.create_web_source(first_person.id, source)
    second_link = await service.create_web_source(second_person.id, source)

    assert first_link.bibliography_id == second_link.bibliography_id
    assert [link.id for link in await service.list_sources(first_person.id)] == [first_link.id]
    bibliography = (
        await db_session.execute(
            select(Bibliography).where(Bibliography.url == "https://example.test/shared-biography")
        )
    ).scalar_one()
    assert bibliography.title == "Wspólny oficjalny biogram"

    with pytest.raises(PersonSourceConflictError, match="już przypisany"):
        await service.create_web_source(first_person.id, source)
