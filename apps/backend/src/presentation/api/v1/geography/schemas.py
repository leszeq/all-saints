"""
Pydantic v2 schemas for Geography & Sacred Places (Country, Region, Diocese, Place, Church).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from src.domain.geography.models import ChurchType, OrderCharism


# ==============================================================================
# COUNTRY SCHEMAS
# ==============================================================================


class CountryCreateSchema(BaseModel):
    name_pl: str = Field(..., min_length=2, max_length=200)
    name_en: str = Field(..., min_length=2, max_length=200)
    name_la: str | None = Field(None, max_length=200)
    name_local: str | None = Field(None, max_length=200)
    iso_code_alpha2: str | None = Field(None, min_length=2, max_length=2)
    iso_code_alpha3: str | None = Field(None, min_length=3, max_length=3)
    continent: str | None = Field(None, max_length=50)
    capital: str | None = Field(None, max_length=200)
    flag_emoji: str | None = Field(None, max_length=10)
    is_historical: bool = False
    historical_period: str | None = Field(None, max_length=200)


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


class DioceseCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=400)
    name_la: str | None = Field(None, max_length=400)
    is_archdiocese: bool = False
    country_id: uuid.UUID | None = None
    founded_year: int | None = None
    suppressed_year: int | None = None


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


class PlaceCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=400)
    name_la: str | None = Field(None, max_length=400)
    name_local: str | None = Field(None, max_length=400)
    description: str | None = None
    country_id: uuid.UUID | None = None
    region_id: uuid.UUID | None = None
    diocese_id: uuid.UUID | None = None
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)


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


class ChurchCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=500)
    name_la: str | None = Field(None, max_length=500)
    church_type: ChurchType = Field(default=ChurchType.PARISH)
    description: str | None = None
    place_id: uuid.UUID | None = None
    diocese_id: uuid.UUID | None = None
    address: str | None = Field(None, max_length=500)
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    construction_year: int | None = None
    consecration_year: int | None = None
    website_url: str | None = Field(None, max_length=500)
    is_pilgrimage_site: bool = False
    is_national_sanctuary: bool = False


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
