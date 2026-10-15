"""Shared policy for mutations that change an already published profile."""

from __future__ import annotations

from src.domain.hagiography.models import Person, PublicationStatus


class PublishedContentChangeError(PermissionError):
    """Raised when a published profile is changed without publication rights."""

    def __init__(self) -> None:
        super().__init__("Edycja opublikowanego profilu wymaga uprawnienia persons:publish")


def require_published_change_permission(
    person: Person,
    *,
    allow_published_update: bool,
) -> None:
    """Reject public-profile mutations unless the caller can publish content."""
    status_value = person.status.value if hasattr(person.status, "value") else str(person.status)
    if status_value == PublicationStatus.PUBLISHED.value and not allow_published_update:
        raise PublishedContentChangeError
