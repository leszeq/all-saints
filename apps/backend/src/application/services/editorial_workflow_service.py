"""Publication workflow transitions for editorial person records."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonUpdateSchema
from src.application.editorial_models import EditorialTransitionResponseSchema
from src.application.services.audit_service import AuditContext
from src.application.services.editorial_quality import EditorialQualityPolicy
from src.application.services.person_query_service import PersonQueryService
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import Person, PublicationStatus
from src.domain.sources.models import ImageLicense


class EditorialNotFoundError(ValueError):
    """Raised when a workflow target cannot be found."""


class EditorialTransitionError(ValueError):
    """Raised when a publication transition is not allowed."""


class EditorialAuthorizationError(ValueError):
    """Raised when a workflow transition requires publication permission."""


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    PublicationStatus.DRAFT.value: {PublicationStatus.REVIEW.value},
    PublicationStatus.REVIEW.value: {
        PublicationStatus.DRAFT.value,
        PublicationStatus.PUBLISHED.value,
    },
    PublicationStatus.PUBLISHED.value: {
        PublicationStatus.REVIEW.value,
        PublicationStatus.ARCHIVED.value,
    },
    PublicationStatus.ARCHIVED.value: {PublicationStatus.DRAFT.value},
}

TRANSITION_PERMISSIONS: dict[tuple[str, str], str] = {
    (PublicationStatus.DRAFT.value, PublicationStatus.REVIEW.value): "persons:submit",
    (PublicationStatus.REVIEW.value, PublicationStatus.DRAFT.value): "persons:review",
    (PublicationStatus.REVIEW.value, PublicationStatus.PUBLISHED.value): "persons:review",
    (PublicationStatus.PUBLISHED.value, PublicationStatus.REVIEW.value): "persons:publish",
    (PublicationStatus.PUBLISHED.value, PublicationStatus.ARCHIVED.value): "persons:publish",
    (PublicationStatus.ARCHIVED.value, PublicationStatus.DRAFT.value): "persons:publish",
}


class EditorialWorkflowService:
    """Validate and persist one allowed editorial status transition."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def transition(
        self,
        person_id: uuid.UUID,
        target_status: PublicationStatus,
        *,
        user_id: uuid.UUID,
        note: str | None = None,
        granted_permissions: set[str] | None = None,
        expected_version: int | None = None,
        audit_context: AuditContext | None = None,
    ) -> EditorialTransitionResponseSchema:
        """Apply one allowed workflow transition and write a version snapshot."""
        person = await PersonQueryService(self.db).get_by_id_or_slug(str(person_id))
        if person is None:
            raise EditorialNotFoundError("Rekord nie istnieje")
        previous = str(person.status)
        if target_status.value not in ALLOWED_TRANSITIONS.get(previous, set()):
            raise EditorialTransitionError(
                f"Przejście {previous} → {target_status.value} nie jest dozwolone"
            )
        required_permission = TRANSITION_PERMISSIONS[(previous, target_status.value)]
        if required_permission not in (granted_permissions or set()):
            raise EditorialAuthorizationError(
                f"Ta operacja wymaga uprawnienia {required_permission}"
            )
        normalized_note = note.strip() if note else None
        if (
            previous == PublicationStatus.REVIEW.value
            and target_status == PublicationStatus.DRAFT
            and not normalized_note
        ):
            raise EditorialTransitionError(
                "Zwrócenie rekordu do redaktora wymaga komentarza z uzasadnieniem"
            )
        if target_status == PublicationStatus.PUBLISHED:
            source_count = int(
                (
                    await self.db.execute(
                        select(EditorialQualityPolicy.source_count_expression()).where(
                            Person.id == person.id
                        )
                    )
                ).scalar_one()
                or 0
            )
            active_images = [image for image in person.images if image.deleted_at is None]
            blockers = EditorialQualityPolicy.publication_blockers(
                person,
                source_count=source_count,
                image_count=len(active_images),
                unknown_license_count=sum(
                    image.license == ImageLicense.UNKNOWN.value for image in active_images
                ),
            )
            if blockers:
                raise EditorialTransitionError(
                    "Publikacja wymaga uzupełnienia: "
                    + ", ".join(issue.label.lower() for issue in blockers)
                )
        summary = normalized_note or f"Workflow redakcyjny: {previous} → {target_status.value}"
        person = await PersonService(self.db).update_person(
            person,
            PersonUpdateSchema(
                status=target_status,
                change_summary=summary,
                expected_version=expected_version,
            ),
            user_id=user_id,
            allow_status_change=True,
            audit_context=audit_context,
        )
        return EditorialTransitionResponseSchema(
            person_id=person.id,
            previous_status=previous,
            status=person.status,
            updated_at=person.updated_at,
        )
