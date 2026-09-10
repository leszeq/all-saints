"""Versioned JSON contract for importing religious communities."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.application.commands.religious_orders import CreateReligiousOrderCommand

ORDER_IMPORT_SCHEMA_VERSION: Literal[1] = 1


class PortableReligiousOrder(CreateReligiousOrderCommand):
    """One complete community record accepted by the JSON importer."""

    model_config = ConfigDict(extra="forbid")


class ReligiousOrderImportDocument(BaseModel):
    """Versioned envelope for an atomic batch of religious communities."""

    schema_version: Literal[1] = ORDER_IMPORT_SCHEMA_VERSION
    orders: list[PortableReligiousOrder] = Field(..., min_length=1, max_length=100)

    model_config = ConfigDict(extra="forbid")


class ReligiousOrderImportValidationResult(BaseModel):
    """Read-only validation result displayed before the batch is persisted."""

    can_import: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    normalized_document: ReligiousOrderImportDocument
