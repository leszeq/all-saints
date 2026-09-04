"""Build the editorial AI suggestion queue from current person records."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import and_, func
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from src.application.ai_models import AISuggestionResult, AISuggestionsPageResult
from src.domain.hagiography.models import Person, PublicationStatus


def active_person_filter() -> ColumnElement[bool]:
    """Return the common filter for records visible to editorial tooling."""
    return and_(
        Person.deleted_at.is_(None),
        Person.status != PublicationStatus.ARCHIVED.value,
    )


def has_text_expression(
    column: InstrumentedAttribute[str | None],
) -> ColumnElement[bool]:
    """Check whether a nullable SQL text column contains text."""
    return and_(column.is_not(None), func.length(func.trim(column)) > 0)


def has_text_value(value: str | None) -> bool:
    """Return True when a Python string contains non-whitespace text."""
    return bool(value and value.strip())


def preview(value: str | None, max_length: int = 360) -> str | None:
    """Trim long text values for compact API responses."""
    if not value or not value.strip():
        return None
    normalized = " ".join(value.strip().split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 1].rstrip()}…"


def tag_list(value: object) -> list[str]:
    """Normalize AI tags persisted as JSON into a printable string list."""
    if not isinstance(value, list):
        return []
    return [str(tag).strip() for tag in value if str(tag).strip()]


class AISuggestionBuilder:
    """Map people to non-destructive AI proposals for editorial review."""

    def __init__(self, *, embedding_disabled: bool, tagging_disabled: bool) -> None:
        self._embedding_disabled = embedding_disabled
        self._tagging_disabled = tagging_disabled

    def for_person(self, person: Person) -> list[AISuggestionResult]:
        suggestions: list[AISuggestionResult] = []
        action_href = f"/dashboard/persons/{person.id}/edit"
        biography = person.biography_pl or ""
        summary = person.summary_pl or ""
        has_biography = has_text_value(biography)

        if person.embedding is None:
            status = "blocked" if self._embedding_disabled else "ready_to_generate"
            suggestions.append(
                AISuggestionResult(
                    id=f"embedding:{person.id}",
                    person_id=person.id,
                    person_slug=person.slug,
                    person_name=person.canonical_name,
                    kind="embedding",
                    status=status,
                    title="Brak embeddingu semantycznego",
                    description=(
                        "Profil nie będzie brany pod uwagę w wyszukiwaniu "
                        "semantycznym ani w rekomendacjach pokrewnych postaci."
                    ),
                    current_value=None,
                    suggested_value=("Wygeneruj wektor z imienia, streszczenia, epoki i biogramu."),
                    confidence=90 if not self._embedding_disabled else 0,
                    reason=(
                        "Dostawca embeddingów jest wyłączony."
                        if self._embedding_disabled
                        else "Brakuje rekordu w tabeli person_embeddings."
                    ),
                    action="generate_embedding",
                    action_href=action_href,
                    updated_at=person.updated_at,
                )
            )

        if has_text_value(person.ai_summary):
            suggestions.append(
                AISuggestionResult(
                    id=f"summary:{person.id}",
                    person_id=person.id,
                    person_slug=person.slug,
                    person_name=person.canonical_name,
                    kind="summary",
                    status="pending_review",
                    title="Streszczenie AI czeka na decyzję",
                    description=(
                        "AI zapisało propozycję streszczenia. Redaktor powinien "
                        "porównać ją z aktualnym streszczeniem i przepisać tylko "
                        "zaakceptowaną wersję."
                    ),
                    current_value=preview(summary),
                    suggested_value=preview(person.ai_summary),
                    confidence=82,
                    reason="Propozycja AI jest przechowywana osobno od treści redakcyjnej.",
                    action="review_person",
                    action_href=action_href,
                    updated_at=person.updated_at,
                )
            )
        elif has_biography:
            suggestions.append(
                AISuggestionResult(
                    id=f"summary:{person.id}",
                    person_id=person.id,
                    person_slug=person.slug,
                    person_name=person.canonical_name,
                    kind="summary",
                    status="ready_to_generate",
                    title="Można przygotować streszczenie AI",
                    description=(
                        "Biogram jest uzupełniony, więc system może wygenerować "
                        "krótką syntezę do weryfikacji redaktora."
                    ),
                    current_value=preview(summary),
                    suggested_value=("Wygeneruj propozycję streszczenia na podstawie biogramu."),
                    confidence=70,
                    reason="Biogram zawiera tekst, a pole ai_summary jest puste.",
                    action="generate_summary",
                    action_href=action_href,
                    updated_at=person.updated_at,
                )
            )

        ai_tags = tag_list(person.ai_tags)
        if ai_tags:
            suggestions.append(
                AISuggestionResult(
                    id=f"tags:{person.id}",
                    person_id=person.id,
                    person_slug=person.slug,
                    person_name=person.canonical_name,
                    kind="tags",
                    status="pending_review",
                    title="Tagi AI czekają na mapowanie",
                    description=(
                        "AI zaproponowało tagi tematyczne. Redaktor może użyć ich "
                        "jako podpowiedzi przy pracy ze słownikiem tagów i patronatów."
                    ),
                    current_value=None,
                    suggested_value=", ".join(ai_tags),
                    confidence=78,
                    reason="Tagi AI nie nadpisują słownika redakcyjnego automatycznie.",
                    action="review_person",
                    action_href=action_href,
                    updated_at=person.updated_at,
                )
            )
        elif has_biography:
            status = "blocked" if self._tagging_disabled else "ready_to_generate"
            suggestions.append(
                AISuggestionResult(
                    id=f"tags:{person.id}",
                    person_id=person.id,
                    person_slug=person.slug,
                    person_name=person.canonical_name,
                    kind="tags",
                    status=status,
                    title="Można przygotować tagi AI",
                    description=(
                        "Na podstawie biogramu można zasugerować patronaty, cnoty, "
                        "miejsca i kategorie tematyczne."
                    ),
                    current_value=None,
                    suggested_value="Wygeneruj 5–10 tagów do weryfikacji redakcyjnej.",
                    confidence=65 if not self._tagging_disabled else 0,
                    reason=(
                        "Automatyczne tagowanie wymaga dostawcy OpenAI albo Ollama."
                        if self._tagging_disabled
                        else "Biogram zawiera tekst, a pole ai_tags jest puste."
                    ),
                    action="generate_tags",
                    action_href=action_href,
                    updated_at=person.updated_at,
                )
            )

        return suggestions

    def page(
        self,
        persons: Iterable[Person],
        *,
        kind_filter: str | None = None,
        status_filter: str | None = None,
        limit: int = 50,
    ) -> AISuggestionsPageResult:
        suggestions = [suggestion for person in persons for suggestion in self.for_person(person)]
        status_rank = {"pending_review": 0, "ready_to_generate": 1, "blocked": 2}
        suggestions.sort(
            key=lambda item: (
                status_rank.get(item.status, 9),
                -item.confidence,
                item.person_name.lower(),
            )
        )

        if kind_filter:
            suggestions = [item for item in suggestions if item.kind == kind_filter]

        pending_review = sum(1 for item in suggestions if item.status == "pending_review")
        ready_to_generate = sum(1 for item in suggestions if item.status == "ready_to_generate")
        blocked = sum(1 for item in suggestions if item.status == "blocked")

        if status_filter:
            suggestions = [item for item in suggestions if item.status == status_filter]

        return AISuggestionsPageResult(
            items=suggestions[:limit],
            total=len(suggestions),
            pending_review=pending_review,
            ready_to_generate=ready_to_generate,
            blocked=blocked,
        )
