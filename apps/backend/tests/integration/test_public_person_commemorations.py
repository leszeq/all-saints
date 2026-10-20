"""Public person commemorations expose only active fixed entries."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import PublicationStatus
from src.domain.liturgy.models import Feast, LiturgicalCalendar


@pytest.mark.asyncio
async def test_public_person_commemorations_filter_visibility_and_expose_coverage(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Św. Kalendarzowy profil")
    )
    person.status = PublicationStatus.PUBLISHED.value
    hidden = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Szkic kalendarzowy")
    )
    polish = LiturgicalCalendar(
        code="test_public_calendar",
        name="Kalendarz testowy",
        rite="roman",
        scope="national",
        description="Stałe wpisy testowe",
        is_active=True,
    )
    inactive = LiturgicalCalendar(
        code="test_inactive_calendar",
        name="Nieaktywny kalendarz",
        rite="roman",
        scope="local",
        is_active=False,
    )
    db_session.add_all([polish, inactive])
    await db_session.flush()
    db_session.add_all(
        [
            Feast(
                person_id=person.id,
                calendar_id=polish.id,
                month=5,
                day=12,
                rank="memorial",
                is_primary=True,
                source_title="Martyrologium testowe",
                source_url="https://example.org/calendar",
            ),
            Feast(
                person_id=person.id,
                calendar_id=polish.id,
                month=5,
                day=13,
                rank="memorial",
                is_moveable=True,
            ),
            Feast(
                person_id=person.id,
                calendar_id=polish.id,
                month=5,
                day=14,
                rank="memorial",
                is_suppressed=True,
            ),
            Feast(
                person_id=person.id,
                calendar_id=inactive.id,
                month=5,
                day=15,
                rank="memorial",
            ),
            Feast(
                person_id=hidden.id,
                calendar_id=polish.id,
                month=5,
                day=16,
                rank="memorial",
            ),
        ]
    )
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/persons/{person.slug}/commemorations"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["month"] == 5
    assert payload[0]["day"] == 12
    assert payload[0]["source_title"] == "Martyrologium testowe"
    assert payload[0]["calendar"]["coverage"] == {
        "coverage_status": "fixed_only",
        "fixed_only": True,
        "coverage_note": (
            "Zakres obejmuje opracowane stałe wpisy; reguły ruchome nie są obecnie rozwiązywane."
        ),
    }


@pytest.mark.asyncio
async def test_public_person_commemorations_hide_unpublished_profiles(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Nieopublikowany kalendarz")
    )
    response = await async_client.get(
        f"/api/v1/persons/{person.slug}/commemorations"
    )

    assert response.status_code == 404
