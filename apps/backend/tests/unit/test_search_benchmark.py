"""Tests for the offline person-search relevance benchmark."""

from pathlib import Path

import pytest

from src.application.search_benchmark import (
    SearchBenchmarkCase,
    SearchBenchmarkFixture,
    evaluate_search_benchmark,
    load_search_benchmark,
    main,
    ndcg_at_k,
    reciprocal_rank,
)

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "data/search/search_gold_v1.json"


def _fixture(case_count: int = 100) -> SearchBenchmarkFixture:
    return SearchBenchmarkFixture(
        version="test-v1",
        cutoff=10,
        top_k=5,
        thresholds={"top_k_success": 0.9},
        cases=tuple(
            SearchBenchmarkCase(
                case_id=f"case-{index}",
                query=f"query {index}",
                expected_slugs=(f"person-{index}",),
                query_class="exact",
            )
            for index in range(case_count)
        ),
    )


def test_gold_fixture_has_reviewable_case_count_and_real_public_slugs() -> None:
    fixture = load_search_benchmark(FIXTURE_PATH)

    assert len(fixture.cases) == 100
    assert {case.query_class for case in fixture.cases} == {
        "canonical_exact",
        "english_exact",
        "latin_exact",
        "accentless",
        "partial",
        "typo",
    }
    assert all(case.expected_slugs[0].startswith(("sw-", "bl-")) for case in fixture.cases)


def test_reciprocal_rank_deduplicates_results_before_counting_position() -> None:
    assert reciprocal_rank(["other", "expected", "expected"], ["expected"], cutoff=10) == 0.5


def test_ndcg_penalizes_a_relevant_result_below_the_first_position() -> None:
    assert ndcg_at_k(["other", "expected"], ["expected"], cutoff=10) == pytest.approx(
        1 / 1.5849625007
    )


def test_evaluate_search_benchmark_reports_ideal_results() -> None:
    fixture = _fixture()
    ranked = {case.case_id: [case.expected_slugs[0]] for case in fixture.cases}

    report = evaluate_search_benchmark(fixture, ranked)

    assert report.evaluated_cases == 100
    assert report.top_k_success == 1.0
    assert report.mrr_at_cutoff == 1.0
    assert report.ndcg_at_cutoff == 1.0
    assert report.zero_results_rate == 0.0
    assert report.threshold_failures(fixture.thresholds) == ()


def test_evaluate_search_benchmark_treats_missing_adapter_rows_as_zero_results() -> None:
    fixture = _fixture()

    report = evaluate_search_benchmark(fixture, {})

    assert report.top_k_success == 0.0
    assert report.mrr_at_cutoff == 0.0
    assert report.ndcg_at_cutoff == 0.0
    assert report.zero_results_rate == 1.0
    assert report.threshold_failures(fixture.thresholds) == ("top_k_success",)


def test_cli_emits_metrics_and_fails_check_when_threshold_is_missed(tmp_path, capsys) -> None:
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        FIXTURE_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    results_path = tmp_path / "results.json"
    results_path.write_text("{}", encoding="utf-8")

    exit_code = main(["--fixture", str(fixture_path), "--results", str(results_path), "--check"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert '"evaluated_cases": 100' in captured.out
    assert "Benchmark thresholds missed" in captured.err
