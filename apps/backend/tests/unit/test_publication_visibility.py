"""Regression checks for publication visibility outside the editorial panel."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.order_service import OrderService
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import PersonSort
from src.main import app


@pytest.mark.asyncio
async def test_public_person_list_query_forces_published_status() -> None:
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    await PersonService(db).list_persons(published_only=True)

    for call in db.execute.await_args_list:
        assert "published" in call.args[0].compile().params.values()


@pytest.mark.asyncio
async def test_public_person_list_can_order_by_latest_update() -> None:
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    await PersonService(db).list_persons(
        published_only=True,
        sort=PersonSort.UPDATED_DESC,
    )

    statement = db.execute.await_args_list[1].args[0]
    assert "ORDER BY persons.updated_at DESC, persons.canonical_name ASC" in str(statement)


@pytest.mark.asyncio
async def test_public_person_detail_query_forces_published_status() -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    person = await PersonService(db).get_by_id_or_slug(
        "nieopublikowany-szkic",
        published_only=True,
    )

    assert person is None
    assert "published" in db.execute.await_args.args[0].compile().params.values()


@pytest.mark.asyncio
async def test_public_order_counts_include_only_published_members() -> None:
    result = MagicMock()
    result.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    await OrderService(db).list_orders()

    statement = db.execute.await_args.args[0]
    assert "published" in statement.compile().params.values()


def test_public_contract_hides_status_filter_and_protects_editorial_detail() -> None:
    schema = app.openapi()
    public_parameters = schema["paths"]["/api/v1/persons"]["get"]["parameters"]
    admin_detail = schema["paths"]["/api/v1/persons/admin/{id_or_slug}"]["get"]

    assert "status" not in {parameter["name"] for parameter in public_parameters}
    assert "sort" in {parameter["name"] for parameter in public_parameters}
    assert "locale" in {parameter["name"] for parameter in public_parameters}
    assert (
        "localized_content" in schema["components"]["schemas"]["PersonListItemSchema"]["properties"]
    )
    assert admin_detail["security"] == [{"HTTPBearer": []}]
