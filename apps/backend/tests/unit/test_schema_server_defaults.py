"""Keep ORM server defaults aligned with the executable schema."""

from __future__ import annotations

from src.domain.base import Base

EXPECTED_SERVER_DEFAULTS = {
    "audit_logs": {"id": "gen_random_uuid()", "created_at": "now()"},
    "bibliography": {"source_type": "'book'"},
    "categories": {"sort_order": "0"},
    "churches": {
        "church_type": "'parish'",
        "is_pilgrimage_site": "false",
        "is_national_sanctuary": "false",
    },
    "countries": {"is_historical": "false"},
    "dioceses": {"is_archdiocese": "false"},
    "documents": {"document_type": "'other'", "is_public": "true"},
    "feasts": {
        "is_moveable": "false",
        "rank": "'memorial'",
        "is_primary": "false",
        "is_suppressed": "false",
    },
    "historical_sources": {
        "source_type": "'manuscript'",
        "is_digitized": "false",
    },
    "images": {"license": "'unknown'", "is_primary": "false", "sort_order": "0"},
    "liturgical_calendars": {
        "rite": "'roman'",
        "scope": "'universal'",
        "is_active": "true",
    },
    "miracles": {
        "verification_status": "'reported'",
        "used_for_beatification": "false",
        "used_for_canonization": "false",
    },
    "patronages": {"is_official": "false"},
    "person_embeddings": {
        "provider": "'disabled'",
        "model": "'text-embedding-3-small'",
    },
    "person_orders": {"is_founder": "false", "membership_type": "'member'"},
    "person_quotes": {"is_attributed": "true"},
    "person_relationships": {"is_bidirectional": "true"},
    "person_sources": {"is_primary": "false"},
    "person_versions": {"id": "gen_random_uuid()"},
    "persons": {
        "person_type": "'saint'",
        "status": "'draft'",
        "gender": "'unknown'",
        "is_featured": "false",
    },
    "relics": {"is_authenticated": "false"},
    "religious_orders": {
        "community_type": "'religious_order'",
        "is_suppressed": "false",
        "is_featured": "false",
        "sort_order": "0",
    },
    "roles": {"is_system": "false"},
    "users": {
        "status": "'pending_verification'",
        "preferred_language": "'pl'",
        "is_verified": "false",
        "is_two_factor_enabled": "false",
        "failed_login_attempts": "0",
    },
}


def test_domain_server_defaults_match_migrated_values() -> None:
    for table_name, expected_columns in EXPECTED_SERVER_DEFAULTS.items():
        table = Base.metadata.tables[table_name]
        for column_name, expected_default in expected_columns.items():
            default = table.c[column_name].server_default
            assert default is not None, f"{table_name}.{column_name} has no server default"
            assert str(default.arg) == expected_default
