"""Contract tests for editorial person-translation route composition."""

from src.main import app


def test_person_translation_routes_remain_bearer_protected() -> None:
    paths = app.openapi()["paths"]
    collection = paths["/api/v1/persons/{person_id}/translations"]
    detail = paths["/api/v1/persons/{person_id}/translations/{language_code}"]

    for operation in (
        collection["get"],
        collection["post"],
        detail["patch"],
        detail["delete"],
    ):
        assert operation["security"] == [{"HTTPBearer": []}]


def test_person_translation_language_contract_remains_documented() -> None:
    detail = app.openapi()["paths"]["/api/v1/persons/{person_id}/translations/{language_code}"]
    language_parameter = next(
        parameter
        for parameter in detail["patch"]["parameters"]
        if parameter["name"] == "language_code"
    )

    assert language_parameter["schema"]["pattern"] == (r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*$")
