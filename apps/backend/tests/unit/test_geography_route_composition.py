"""Contract tests for geography route composition."""

from src.main import app


def test_geography_routes_preserve_public_and_editorial_security_boundaries() -> None:
    paths = app.openapi()["paths"]

    for resource in ("countries", "dioceses", "places", "churches"):
        operations = paths[f"/api/v1/geography/{resource}"]

        assert "security" not in operations["get"]
        assert operations["post"]["security"] == [{"HTTPBearer": []}]
