"""Public citations: bibliographic facts without editorial notes or evaluations."""

import uuid

from pydantic import BaseModel, ConfigDict

from src.domain.sources.models import PersonSource


class PublicBibliographySchema(BaseModel):
    title: str
    subtitle: str | None = None
    source_type: str
    authors: str | None = None
    editor: str | None = None
    publisher: str | None = None
    place_of_publication: str | None = None
    year: int | None = None
    edition: str | None = None
    volume: str | None = None
    pages: str | None = None
    isbn: str | None = None
    issn: str | None = None
    doi: str | None = None
    url: str | None = None
    url_access_date: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PublicHistoricalSourceSchema(BaseModel):
    title: str
    original_title: str | None = None
    source_type: str
    repository: str | None = None
    call_number: str | None = None
    date_range: str | None = None
    digitization_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PublicPersonSourceSchema(BaseModel):
    id: uuid.UUID
    page_reference: str | None = None
    is_primary: bool
    bibliography: PublicBibliographySchema | None = None
    historical_source: PublicHistoricalSourceSchema | None = None

    @classmethod
    def from_link(cls, link: PersonSource) -> "PublicPersonSourceSchema":
        bibliography = link.bibliography
        historical = link.historical_source
        return cls(
            id=link.id,
            page_reference=link.page_reference,
            is_primary=link.is_primary,
            bibliography=(
                PublicBibliographySchema.model_validate(bibliography)
                if bibliography is not None and bibliography.deleted_at is None
                else None
            ),
            historical_source=(
                PublicHistoricalSourceSchema.model_validate(historical)
                if historical is not None and historical.deleted_at is None
                else None
            ),
        )
