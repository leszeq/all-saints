"""Regression tests for the incremental backend dependency boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).parents[2]
SRC_ROOT = BACKEND_ROOT / "src"

# Existing debt is removed vertically. Files disappear from this allowlist as
# their input/output models move below the presentation layer.
ALLOWED_PRESENTATION_DEPENDENCIES = {
    "application/services/calendar_service.py",
    "application/services/editorial_quality.py",
    "application/services/editorial_service.py",
    "application/services/editorial_source_quality.py",
    "application/services/person_service.py",
}


def _presentation_dependencies(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "src.presentation"
        ):
            dependencies.add(node.module or "")
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
            if dependencies and relative_path not in ALLOWED_PRESENTATION_DEPENDENCIES:
                violations[relative_path] = dependencies

    assert violations == {}
