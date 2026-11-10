"""Shared publication gate for editorial workflows and quality reporting."""

from __future__ import annotations

from collections.abc import Iterable

from src.application.editorial_models import EditorialIssueSchema


class PublicationPolicy:
    """Keep publication blockers and their user-facing order in one place."""

    BLOCKER_CODES = frozenset(
        {"missing_biography", "missing_summary", "missing_sources", "unknown_image_license"}
    )
    _ORDER = {
        "missing_summary": 0,
        "missing_biography": 1,
        "missing_sources": 2,
        "unknown_image_license": 3,
    }

    @classmethod
    def blockers(cls, issues: Iterable[EditorialIssueSchema]) -> list[EditorialIssueSchema]:
        """Return only publication blockers in a stable editorial order."""
        return sorted(
            (issue for issue in issues if issue.code in cls.BLOCKER_CODES),
            key=lambda issue: cls._ORDER[issue.code],
        )

    @staticmethod
    def rejection_message(blockers: Iterable[EditorialIssueSchema]) -> str:
        """Build the same actionable error for every publication entry point."""
        labels = [issue.label.lower() for issue in blockers]
        return "Publikacja wymaga uzupełnienia: " + ", ".join(labels)
