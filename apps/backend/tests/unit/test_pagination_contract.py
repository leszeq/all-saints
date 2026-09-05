"""Regression coverage for the documented pagination API contract."""

from __future__ import annotations

from fastapi import Response

from src.main import app
from src.presentation.api.pagination import add_pagination_headers

PAGINATED_PATHS = (
    "/api/v1/geography/dioceses",
    "/api/v1/geography/places",
    "/api/v1/geography/churches",
    "/api/v1/sources/bibliography",
    "/api/v1/sources/historical-sources",
    "/api/v1/sources/images",
    "/api/v1/sources/documents",
    "/api/v1/taxonomy/tags",
    "/api/v1/taxonomy/occupations",
)


def test_pagination_headers_include_an_empty_total() -> None:
    response = Response()

    add_pagination_headers(response, total=0, page=1, per_page=100)

    assert response.headers["x-total-count"] == "0"
    assert response.headers["x-total-pages"] == "0"


def test_openapi_documents_shared_page_parameters_and_headers() -> None:
    schema = app.openapi()

    for path in PAGINATED_PATHS:
        operation = schema["paths"][path]["get"]
        parameter_names = {parameter["name"] for parameter in operation["parameters"]}
        response_headers = operation["responses"]["200"]["headers"]

        assert {"page", "per_page"} <= parameter_names
        assert {
            "X-Total-Count",
            "X-Page",
            "X-Per-Page",
            "X-Total-Pages",
        } <= set(response_headers)

    image_parameters = {
        parameter["name"]: parameter
        for parameter in schema["paths"]["/api/v1/sources/images"]["get"]["parameters"]
    }
    assert image_parameters["limit"]["deprecated"] is True
