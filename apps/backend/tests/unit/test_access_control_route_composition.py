"""Contract tests for user and role route composition."""

from src.main import app


def test_user_and_role_administration_routes_remain_bearer_protected() -> None:
    paths = app.openapi()["paths"]

    operations = (
        paths["/api/v1/users"]["get"],
        paths["/api/v1/users"]["post"],
        paths["/api/v1/users/{user_id}"]["patch"],
        paths["/api/v1/users/{user_id}"]["delete"],
        paths["/api/v1/roles"]["get"],
        paths["/api/v1/roles"]["post"],
        paths["/api/v1/roles/{role_id}"]["patch"],
        paths["/api/v1/roles/{role_id}"]["delete"],
    )

    assert all(operation["security"] == [{"HTTPBearer": []}] for operation in operations)
