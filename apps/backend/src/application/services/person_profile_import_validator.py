"""Read-only validation and normalization of portable person profile documents."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.person_profile_models import (
    PersonProfileDocument,
    PersonProfileValidationResult,
)
from src.domain.geography.models import Country, Place, ReligiousOrder
from src.domain.hagiography.models import Person, PublicationStatus, StateOfLife
from src.domain.liturgy.models import Feast, LiturgicalCalendar


class PersonProfileImportValidator:
    """Validate imports and produce a safe normalized document without writes."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate_import(
        self, document: PersonProfileDocument
    ) -> PersonProfileValidationResult:
        """Check duplicates and every database reference without mutating data."""
        normalized = document.model_copy(deep=True)
        warnings: list[str] = []
        errors: list[str] = []
        if normalized.profile.status != PublicationStatus.DRAFT:
            warnings.append(
                "Status z pliku zostanie zmieniony na szkic; import nie omija procesu redakcyjnego."
            )
            normalized.profile.status = PublicationStatus.DRAFT

        duplicate = (
            await self.db.execute(
                select(Person.id)
                .where(
                    Person.deleted_at.is_(None),
                    func.lower(Person.canonical_name)
                    == normalized.profile.canonical_name.strip().lower(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            errors.append("Aktywny profil o tej samej nazwie kanonicznej już istnieje.")

        reference_checks = (
            ("birth_country_id", Country, "Kraj urodzenia"),
            ("death_country_id", Country, "Kraj śmierci"),
            ("nationality_id", Country, "Narodowość"),
            ("birth_place_id", Place, "Miejsce urodzenia"),
            ("death_place_id", Place, "Miejsce śmierci"),
            ("state_of_life_id", StateOfLife, "Stan życia"),
        )
        for field, model, label in reference_checks:
            identifier = getattr(normalized.profile, field)
            if identifier is not None:
                reference = await self.db.get(model, identifier)
                if reference is None or getattr(reference, "deleted_at", None) is not None:
                    errors.append(f"{label}: wskazany identyfikator nie istnieje w tej bazie.")

        order_slugs = [membership.order_slug for membership in normalized.orders]
        if len(order_slugs) != len(set(order_slugs)):
            errors.append("Ten sam zakon nie może być przypisany do profilu więcej niż raz.")
        if order_slugs:
            existing_orders = set(
                (
                    await self.db.execute(
                        select(ReligiousOrder.slug).where(
                            ReligiousOrder.slug.in_(order_slugs),
                            ReligiousOrder.deleted_at.is_(None),
                        )
                    )
                ).scalars()
            )
            for missing_slug in sorted(set(order_slugs) - existing_orders):
                errors.append(f"Nie znaleziono wspólnoty o slugu: {missing_slug}.")

        calendar_codes = [entry.calendar_code for entry in normalized.feasts]
        if calendar_codes:
            existing_calendars = set(
                (
                    await self.db.execute(
                        select(LiturgicalCalendar.code).where(
                            LiturgicalCalendar.code.in_(calendar_codes),
                            LiturgicalCalendar.deleted_at.is_(None),
                            LiturgicalCalendar.is_active.is_(True),
                        )
                    )
                ).scalars()
            )
            for missing_code in sorted(set(calendar_codes) - existing_calendars):
                errors.append(f"Nie znaleziono aktywnego kalendarza: {missing_code}.")

        for entry in normalized.feasts:
            try:
                date(2000, entry.month, entry.day)
            except ValueError:
                errors.append(f"Nieprawidłowa data wspomnienia: {entry.month:02d}-{entry.day:02d}.")

        feast_keys = [(entry.calendar_code, entry.month, entry.day) for entry in normalized.feasts]
        if len(feast_keys) != len(set(feast_keys)):
            errors.append("Profil zawiera powtórzone wspomnienie w tym samym kalendarzu i dniu.")

        for entry in normalized.feasts:
            if not entry.is_primary:
                continue
            existing_primary = (
                await self.db.execute(
                    select(Feast.id)
                    .join(Feast.calendar)
                    .where(
                        LiturgicalCalendar.code == entry.calendar_code,
                        Feast.month == entry.month,
                        Feast.day == entry.day,
                        Feast.is_primary.is_(True),
                        Feast.deleted_at.is_(None),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if existing_primary is not None:
                entry.is_primary = False
                warnings.append(
                    f"W dniu {entry.day:02d}.{entry.month:02d} kalendarz "
                    f"{entry.calendar_code} ma już główny wpis; importowane wspomnienie "
                    "zostanie dodane jako dodatkowe."
                )

        return PersonProfileValidationResult(
            can_import=not errors,
            errors=errors,
            warnings=warnings,
            normalized_document=normalized,
        )
