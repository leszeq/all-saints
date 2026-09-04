"""Normalization policy shared by person aliases and catalogue search."""

from __future__ import annotations

from slugify import slugify


def normalize_person_name(value: str) -> str:
    """Return an accent-insensitive, punctuation-free comparison form."""
    return " ".join(slugify(value, separator=" ").split())
