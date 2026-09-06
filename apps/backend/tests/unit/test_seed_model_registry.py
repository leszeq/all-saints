"""Regression check for ORM model registration in the standalone seed command."""

from pathlib import Path

SEED_MODULE = Path(__file__).parents[2] / "src" / "infrastructure" / "db" / "seed.py"
BACKFILL_MODULE = (
    Path(__file__).parents[2] / "src" / "infrastructure" / "db" / "backfill_person_translations.py"
)


def test_standalone_seed_registers_person_embedding_mapper() -> None:
    source = SEED_MODULE.read_text(encoding="utf-8")

    assert "hagiography import embedding_model" in source


def test_standalone_translation_backfill_registers_related_domain_mappers() -> None:
    source = BACKFILL_MODULE.read_text(encoding="utf-8")

    for model_module in (
        "geography import models",
        "hagiography import embedding_model",
        "identity import models",
        "liturgy import models",
        "sources import models",
    ):
        assert model_module in source
