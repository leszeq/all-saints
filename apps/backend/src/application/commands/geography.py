"""Validated application commands for geography reference data."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from src.domain.geography.models import ChurchType


class CreateCountryCommand(BaseModel):
    """Input required to create a country or historical territory."""

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


class CreateDioceseCommand(BaseModel):
    """Input required to create a diocese or archdiocese."""

    name: str = Field(..., min_length=2, max_length=400)
    name_la: str | None = Field(None, max_length=400)
    is_archdiocese: bool = False
    country_id: uuid.UUID | None = None
    founded_year: int | None = None
    suppressed_year: int | None = None


class CreatePlaceCommand(BaseModel):
    """Input required to create a geographic place."""

    name: str = Field(..., min_length=2, max_length=400)
    name_la: str | None = Field(None, max_length=400)
    name_local: str | None = Field(None, max_length=400)
    description: str | None = None
    country_id: uuid.UUID | None = None
    region_id: uuid.UUID | None = None
    diocese_id: uuid.UUID | None = None
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)


class CreateChurchCommand(BaseModel):
    """Input required to create a church or pilgrimage site."""

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
