"""Regression tests for person avatars backed by primary media records."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from alembic.config import Config
from alembic.script import ScriptDirectory
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import Person
from src.domain.sources.models import Image
from src.main import app
from src.presentation.api.v1.persons.schemas import (
    PersonAvatarInputSchema,
    PersonListItemSchema,
)


def test_avatar_migration_is_in_single_head_history() -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    revisions = {revision.revision for revision in scripts.walk_revisions()}
    assert scripts.get_current_head() is not None
    assert len(scripts.get_heads()) == 1
    assert "0004_unique_primary_person_image" in revisions


def test_avatar_input_accepts_relative_and_https_urls() -> None:
    relative = PersonAvatarInputSchema(url="/media/saint.jpg")
    remote = PersonAvatarInputSchema(url="https://example.org/saint.jpg")

    assert relative.url == "/media/saint.jpg"
    assert remote.url == "https://example.org/saint.jpg"


def test_avatar_input_rejects_unsafe_url_scheme() -> None:
    with pytest.raises(ValidationError, match="HTTP"):
        PersonAvatarInputSchema(url="javascript:alert(1)")


def test_avatar_input_rejects_non_string_url() -> None:
    with pytest.raises(ValidationError, match="tekstem"):
        PersonAvatarInputSchema(url=123)  # type: ignore[arg-type]


def test_person_avatar_returns_only_active_primary_image() -> None:
    now = datetime.now(UTC)
    secondary = Image(
        url="https://example.org/secondary.jpg",
        is_primary=False,
        sort_order=0,
    )
    secondary.deleted_at = None
    secondary.created_at = now
    primary = Image(
        url="https://example.org/avatar.jpg",
        is_primary=True,
        sort_order=1,
    )
    primary.deleted_at = None
    primary.created_at = now
    person = Person()
    person.images = [secondary, primary]

    assert person.avatar is primary


def test_person_list_schema_contains_avatar_metadata() -> None:
    now = datetime.now(UTC)
    avatar = SimpleNamespace(
        id=uuid.uuid4(),
        url="https://example.org/avatar.jpg",
        thumbnail_url=None,
        title="Portret",
        license="public_domain",
        photographer=None,
        source_url="https://example.org/source",
    )
    person = SimpleNamespace(
        id=uuid.uuid4(),
        slug="testowa-postac",
        canonical_name="Św. Testowa Postać",
        canonical_name_en=None,
        person_type="saint",
        status="draft",
        gender="unknown",
        era=None,
        birth_year=None,
        death_year=None,
        summary_pl=None,
        liturgical_color=None,
        is_featured=False,
        avatar=avatar,
        created_at=now,
        updated_at=now,
    )

    response = PersonListItemSchema.model_validate(person)

    assert response.avatar is not None
    assert response.avatar.url == avatar.url
    assert response.avatar.license.value == "public_domain"


@pytest.mark.asyncio
async def test_avatar_sync_creates_primary_portrait() -> None:
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    service = PersonService(db)
    person = SimpleNamespace(id=uuid.uuid4(), canonical_name="Św. Testowa Postać")
    avatar = PersonAvatarInputSchema(
        url="https://example.org/avatar.jpg",
        license="public_domain",
        storage_key="avatars/2026/08/test.webp",
        width_px=800,
        height_px=1200,
        file_size_bytes=100_000,
        mime_type="image/webp",
    )

    await service._sync_avatar(person, avatar)

    image = db.add.call_args.args[0]
    assert isinstance(image, Image)
    assert image.person_id == person.id
    assert image.is_primary is True
    assert image.image_type == "portrait"
    assert image.license == "public_domain"
    assert image.storage_key == "avatars/2026/08/test.webp"
    assert image.width_px == 800
    assert image.height_px == 1200


def test_openapi_exposes_avatar_in_person_contract() -> None:
    schema = app.openapi()

    properties = schema["components"]["schemas"]["PersonListItemSchema"]["properties"]
    create_properties = schema["components"]["schemas"]["PersonCreateSchema"]["properties"]

    assert "avatar" in properties
    assert "avatar" in create_properties


def test_uploaded_image_route_name_survives_sources_router_composition() -> None:
    path = app.url_path_for(
        "get_uploaded_image",
        object_key="avatars/2026/09/test.webp",
    )

    assert str(path) == "/api/v1/sources/images/files/avatars/2026/09/test.webp"


def test_image_file_openapi_preserves_security_boundary() -> None:
    paths = app.openapi()["paths"]

    upload = paths["/api/v1/sources/images/upload"]["post"]
    read = paths["/api/v1/sources/images/files/{object_key}"]["get"]

    assert upload["security"] == [{"HTTPBearer": []}]
    assert "security" not in read
