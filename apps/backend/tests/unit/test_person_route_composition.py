"""Contract checks for the composed person routers."""

from __future__ import annotations

import uuid

from src.main import app


def test_person_mutation_and_history_routes_survive_router_composition() -> None:
    person_id = uuid.uuid4()

    assert str(app.url_path_for("create_person")) == "/api/v1/persons"
    assert str(app.url_path_for("update_person", person_id=person_id)) == (
        f"/api/v1/persons/{person_id}"
    )
    assert str(app.url_path_for("delete_person", person_id=person_id)) == (
        f"/api/v1/persons/{person_id}"
    )
    assert str(app.url_path_for("restore_person", person_id=person_id)) == (
        f"/api/v1/persons/{person_id}/restore"
    )
    assert str(app.url_path_for("get_person_versions", person_id=person_id)) == (
        f"/api/v1/persons/{person_id}/versions"
    )


def test_person_editorial_operations_remain_protected() -> None:
    paths = app.openapi()["paths"]

    assert paths["/api/v1/persons"]["post"]["security"] == [{"HTTPBearer": []}]
    assert paths["/api/v1/persons/{person_id}"]["patch"]["security"] == [{"HTTPBearer": []}]
    assert paths["/api/v1/persons/{person_id}"]["delete"]["security"] == [{"HTTPBearer": []}]
    assert paths["/api/v1/persons/{person_id}/restore"]["post"]["security"] == [{"HTTPBearer": []}]
    assert paths["/api/v1/persons/{person_id}/versions"]["get"]["security"] == [{"HTTPBearer": []}]
