"""Transport-independent read models for source catalogues."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceStatsResult:
    """Counts exposed by the public source-transparency endpoint."""

    bibliography_sources: int
    historical_sources: int
    person_source_links: int
    documented_persons: int
    total_published_persons: int
    images: int
    unknown_license_images: int
