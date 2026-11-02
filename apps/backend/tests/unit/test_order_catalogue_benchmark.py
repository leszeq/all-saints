"""Unit coverage for the order catalogue benchmark helpers."""

import pytest

from src.infrastructure.db.run_order_catalogue_benchmark import _percentile


def test_percentile_uses_nearest_rank() -> None:
    assert _percentile([4.0, 1.0, 3.0, 2.0], 50) == 2.0
    assert _percentile([4.0, 1.0, 3.0, 2.0], 95) == 4.0


def test_percentile_rejects_empty_samples() -> None:
    with pytest.raises(ValueError, match="sample"):
        _percentile([], 50)
