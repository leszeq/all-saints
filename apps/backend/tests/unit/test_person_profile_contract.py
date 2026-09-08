"""Contract tests for versioned person profile JSON import and export."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.application.person_profile_models import PersonProfileDocument
from src.main import app


def test_minimal_profile_document_accepts_portable_feast_without_person_id() -> None:
    document = PersonProfileDocument.model_validate(
        {
            "schema_version": 1,
            "profile": {
                "canonical_name": "Św. Profil Importowany",
                "person_type": "saint",
                "status": "published",
                "gender": "unknown",
            },
            "orders": [
                {
                    "order_slug": "franciszkanie",
                    "membership_type": "friar",
                    "is_founder": False,
                }
            ],
            "feasts": [
                {
                    "calendar_code": "roman_pl",
                    "month": 10,
                    "day": 4,
                    "rank": "memorial",
                }
            ],
        }
    )

    assert document.profile.canonical_name == "Św. Profil Importowany"
    assert document.orders[0].order_slug == "franciszkanie"
    assert document.feasts[0].day == 4


def test_profile_document_rejects_unknown_version_and_invalid_source_shape() -> None:
    with pytest.raises(ValidationError):
        PersonProfileDocument.model_validate(
            {
                "schema_version": 2,
                "profile": {"canonical_name": "Św. Test"},
            }
        )

    with pytest.raises(ValidationError, match="bibliography"):
        PersonProfileDocument.model_validate(
            {
                "schema_version": 1,
                "profile": {"canonical_name": "Św. Test"},
                "sources": [
                    {
                        "kind": "bibliography",
                        "historical_source": {"title": "Acta testowe"},
                    }
                ],
            }
        )


def test_profile_portability_routes_are_exposed_in_openapi() -> None:
    paths = app.openapi()["paths"]

    export = paths["/api/v1/persons/admin/{id_or_slug}/export"]["get"]
    validate = paths["/api/v1/persons/import/validate"]["post"]
    import_profile = paths["/api/v1/persons/import"]["post"]

    assert export["security"] == [{"HTTPBearer": []}]
    assert validate["security"] == [{"HTTPBearer": []}]
    assert import_profile["security"] == [{"HTTPBearer": []}]
    assert "get" in paths["/api/v1/orders/management"]
