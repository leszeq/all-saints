"""Contract tests for taxonomy route composition."""

from src.main import app


def test_taxonomy_routes_preserve_public_and_editorial_security_boundaries() -> None:
    paths = app.openapi()["paths"]

    for resource in ("categories", "tags", "states-of-life", "occupations"):
        assert "security" not in paths[f"/api/v1/taxonomy/{resource}"]["get"]

    for resource in ("categories", "tags"):
        assert paths[f"/api/v1/taxonomy/{resource}"]["post"]["security"] == [{"HTTPBearer": []}]
