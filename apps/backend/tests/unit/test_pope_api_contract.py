"""Contract tests for pope catalogue boundaries."""

from src.main import app
from src.presentation.api.v1.orders.schemas import PopeCreateSchema as LegacyPopeCreateSchema
from src.presentation.api.v1.popes.schemas import PopeCreateSchema


def test_pope_catalogue_preserves_public_read_and_protected_create() -> None:
    operations = app.openapi()["paths"]["/api/v1/popes"]

    assert "security" not in operations["get"]
    assert operations["post"]["security"] == [{"HTTPBearer": []}]


def test_legacy_order_schema_import_reexports_pope_contract() -> None:
    assert LegacyPopeCreateSchema is PopeCreateSchema
