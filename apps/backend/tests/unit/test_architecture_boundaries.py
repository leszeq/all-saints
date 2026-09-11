"""Regression tests for the incremental backend dependency boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).parents[2]
SRC_ROOT = BACKEND_ROOT / "src"
AUTH_PRESENTATION_ROOT = SRC_ROOT / "presentation" / "api" / "v1" / "auth"


def _resolved_import_module(path: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""

    module_path = path.relative_to(BACKEND_ROOT).with_suffix("")
    package_parts = list(module_path.parts)
    if path.name != "__init__.py":
        package_parts.pop()
    keep = max(0, len(package_parts) - node.level + 1)
    imported_parts = (node.module or "").split(".") if node.module else []
    return ".".join([*package_parts[:keep], *imported_parts])


def _presentation_dependencies(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolved_import_module(path, node)
            if module.startswith("src.presentation"):
                dependencies.add(module)
        elif isinstance(node, ast.Import):
            dependencies.update(
                alias.name for alias in node.names if alias.name.startswith("src.presentation")
            )
    return dependencies


def test_lower_layers_do_not_gain_presentation_dependencies() -> None:
    violations: dict[str, set[str]] = {}
    for layer in ("application", "domain", "infrastructure"):
        for path in (SRC_ROOT / layer).rglob("*.py"):
            dependencies = _presentation_dependencies(path)
            relative_path = str(path.relative_to(SRC_ROOT))
            if dependencies:
                violations[relative_path] = dependencies

    assert violations == {}


def test_relative_presentation_imports_are_resolved() -> None:
    tree = ast.parse("from ...presentation.api import router")
    node = tree.body[0]

    assert isinstance(node, ast.ImportFrom)
    assert (
        _resolved_import_module(SRC_ROOT / "application" / "services" / "example.py", node)
        == "src.presentation.api"
    )


def test_authentication_http_adapters_do_not_own_sql_queries() -> None:
    """Keep authentication persistence in application services."""
    violations: dict[str, set[str]] = {}
    for path in AUTH_PRESENTATION_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("sqlalchemy"):
                module = node.module or ""
                for alias in node.names:
                    if module != "sqlalchemy.ext.asyncio" or alias.name != "AsyncSession":
                        imports.add(f"{module}.{alias.name}")
            elif isinstance(node, ast.Import):
                imports.update(
                    alias.name for alias in node.names if alias.name.startswith("sqlalchemy")
                )
        if imports:
            violations[path.name] = imports

    assert violations == {}
