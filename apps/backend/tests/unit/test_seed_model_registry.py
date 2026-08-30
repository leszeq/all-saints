"""Regression check for ORM model registration in the standalone seed command."""

from pathlib import Path

SEED_MODULE = Path(__file__).parents[2] / "src" / "infrastructure" / "db" / "seed.py"


def test_standalone_seed_registers_person_embedding_mapper() -> None:
    source = SEED_MODULE.read_text(encoding="utf-8")

    assert "hagiography import embedding_model" in source
