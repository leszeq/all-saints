"""Validated commands for the editorial person-translation workflow."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.application.services.person_localization import normalize_content_locale

TRANSLATED_CONTENT_FIELDS = (
    "canonical_name",
    "summary",
    "biography",
    "prayers",
    "iconographic_attributes",
)


def _normalize_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    return normalized or None


class TranslationContentCommand(BaseModel):
    """Shared translated fields; null values intentionally clear existing text."""

    model_config = ConfigDict(extra="forbid")

    canonical_name: str | None = Field(None, max_length=500)
    summary: str | None = None
    biography: str | None = None
    prayers: str | None = None
    iconographic_attributes: str | None = None

    @field_validator(*TRANSLATED_CONTENT_FIELDS, mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return _normalize_text(value)


class CreatePersonTranslationCommand(TranslationContentCommand):
    """Create or restore one locale record for a draft person."""

    language_code: str = Field(
        ...,
        min_length=2,
        max_length=35,
        pattern=r"^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$",
    )
    expected_person_version: int = Field(..., ge=1)

    @field_validator("language_code", mode="before")
    @classmethod
    def normalize_language_code(cls, value: object) -> object:
        return normalize_content_locale(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_content(self) -> CreatePersonTranslationCommand:
        if not any(getattr(self, field) for field in TRANSLATED_CONTENT_FIELDS):
            raise ValueError("Tłumaczenie musi zawierać co najmniej jedno pole treści")
        return self


class UpdatePersonTranslationCommand(TranslationContentCommand):
    """Patch translated content using both parent and relation revisions."""

    expected_person_version: int = Field(..., ge=1)
    expected_version: int = Field(..., ge=1)

    @model_validator(mode="after")
    def require_content_change(self) -> UpdatePersonTranslationCommand:
        if not self.model_fields_set.intersection(TRANSLATED_CONTENT_FIELDS):
            raise ValueError("Aktualizacja nie zawiera żadnego pola tłumaczenia")
        return self
