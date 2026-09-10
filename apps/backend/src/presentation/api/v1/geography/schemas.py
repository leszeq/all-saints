"""
Pydantic v2 schemas for Geography & Sacred Places (Country, Region, Diocese, Place, Church).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.application.commands.geography import (
    CreateChurchCommand,
    CreateCountryCommand,
    CreateDioceseCommand,
    CreatePlaceCommand,
)
from src.domain.geography.models import ChurchType

# ==============================================================================
# COUNTRY SCHEMAS
# ==============================================================================


class CountryCreateSchema(CreateCountryCommand):
    pass


class CountryUpdateSchema(BaseModel):
    name_pl: str | None = Field(None, min_length=2, max_length=200)
    name_en: str | None = Field(None, min_length=2, max_length=200)
    name_la: str | None = None
    name_local: str | None = None
    iso_code_alpha2: str | None = None
    iso_code_alpha3: str | None = None
    continent: str | None = None
    capital: str | None = None
    flag_emoji: str | None = None
    is_historical: bool | None = None
    historical_period: str | None = None


class CountrySchema(CountryCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# DIOCESE SCHEMAS
# ==============================================================================


class DioceseCreateSchema(CreateDioceseCommand):
    pass


class DioceseUpdateSchema(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=400)
    name_la: str | None = None
    is_archdiocese: bool | None = None
    country_id: uuid.UUID | None = None
    founded_year: int | None = None
    suppressed_year: int | None = None


class DioceseSchema(DioceseCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# PLACE SCHEMAS
# ==============================================================================


class PlaceCreateSchema(CreatePlaceCommand):
    pass


class PlaceUpdateSchema(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=400)
    name_la: str | None = None
    name_local: str | None = None
    description: str | None = None
    country_id: uuid.UUID | None = None
    region_id: uuid.UUID | None = None
    diocese_id: uuid.UUID | None = None
    latitude: float | None = None
    longitude: float | None = None


class PlaceSchema(PlaceCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# CHURCH SCHEMAS
# ==============================================================================


class ChurchCreateSchema(CreateChurchCommand):
    pass


class ChurchUpdateSchema(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=500)
    name_la: str | None = None
    church_type: ChurchType | None = None
    description: str | None = None
    place_id: uuid.UUID | None = None
    diocese_id: uuid.UUID | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    construction_year: int | None = None
    consecration_year: int | None = None
    website_url: str | None = None
    is_pilgrimage_site: bool | None = None
    is_national_sanctuary: bool | None = None


class ChurchSchema(ChurchCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
