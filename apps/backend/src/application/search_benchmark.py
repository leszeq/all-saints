"""Offline relevance benchmark for the public person search contract."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SearchBenchmarkCase:
    """One judged query and the public slugs that satisfy it."""

    case_id: str
    query: str
    expected_slugs: tuple[str, ...]
    query_class: str


@dataclass(frozen=True, slots=True)
class SearchBenchmarkFixture:
    """Versioned benchmark metadata and its judged query cases."""

    version: str
    cutoff: int
    top_k: int
    thresholds: dict[str, float]
    cases: tuple[SearchBenchmarkCase, ...]

    def validate(self) -> None:
        """Reject malformed or undersized gold data before a quality check runs."""
        if not self.version.strip():
            raise ValueError("Benchmark version cannot be empty")
        if not 1 <= self.top_k <= self.cutoff:
            raise ValueError("top_k must be between 1 and cutoff")
        if not 100 <= len(self.cases) <= 200:
            raise ValueError("Benchmark must contain between 100 and 200 judged cases")

        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Benchmark case IDs must be unique")
        for case in self.cases:
            if not case.case_id.strip() or not case.query.strip():
                raise ValueError("Benchmark cases require an ID and a query")
            if not case.expected_slugs or any(not slug.strip() for slug in case.expected_slugs):
                raise ValueError(f"Case {case.case_id} requires expected public slugs")


@dataclass(frozen=True, slots=True)
class SearchBenchmarkReport:
    """Aggregate relevance metrics for one benchmark run."""

    evaluated_cases: int
    top_k_success: float
    mrr_at_cutoff: float
    ndcg_at_cutoff: float
    zero_results_rate: float
    cutoff: int
    top_k: int

    def to_dict(self) -> dict[str, float | int]:
        """Serialize metrics for CI logs and release artifacts."""
        return asdict(self)

    def threshold_failures(self, thresholds: dict[str, float]) -> tuple[str, ...]:
        """Return stable metric names whose minimum threshold was not met."""
        values: dict[str, float] = {
            "top_k_success": self.top_k_success,
            "mrr_at_cutoff": self.mrr_at_cutoff,
            "ndcg_at_cutoff": self.ndcg_at_cutoff,
        }
        return tuple(
            name
            for name, minimum in thresholds.items()
            if name not in values or values[name] < minimum
        )


def load_search_benchmark(path: Path) -> SearchBenchmarkFixture:
    """Load and validate a JSON fixture kept outside the production database."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = tuple(
        SearchBenchmarkCase(
            case_id=str(raw_case["case_id"]),
            query=str(raw_case["query"]),
            expected_slugs=tuple(str(slug) for slug in raw_case["expected_slugs"]),
            query_class=str(raw_case["query_class"]),
        )
        for raw_case in payload["cases"]
    )
    fixture = SearchBenchmarkFixture(
        version=str(payload["version"]),
        cutoff=int(payload["cutoff"]),
        top_k=int(payload["top_k"]),
        thresholds={str(key): float(value) for key, value in payload["thresholds"].items()},
        cases=cases,
    )
    fixture.validate()
    return fixture


def _unique_ranked_slugs(ranked_slugs: Sequence[str]) -> tuple[str, ...]:
    """Keep the first rank for a slug so malformed adapters cannot inflate metrics."""
    seen: set[str] = set()
    unique: list[str] = []
    for slug in ranked_slugs:
        if slug not in seen:
            seen.add(slug)
            unique.append(slug)
    return tuple(unique)


def reciprocal_rank(
    ranked_slugs: Sequence[str], expected_slugs: Sequence[str], cutoff: int
) -> float:
    """Return reciprocal rank of the first relevant result up to ``cutoff``."""
    expected = set(expected_slugs)
    for rank, slug in enumerate(_unique_ranked_slugs(ranked_slugs)[:cutoff], start=1):
        if slug in expected:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked_slugs: Sequence[str], expected_slugs: Sequence[str], cutoff: int) -> float:
    """Return binary-relevance nDCG at ``cutoff`` for one query."""
    expected = set(expected_slugs)
    ranked = _unique_ranked_slugs(ranked_slugs)[:cutoff]
    dcg = sum(
        (1.0 if slug in expected else 0.0) / math.log2(rank + 1)
        for rank, slug in enumerate(ranked, start=1)
    )
    ideal_relevant = min(len(expected), cutoff)
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_relevant + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def evaluate_search_benchmark(
    fixture: SearchBenchmarkFixture,
    ranked_results: dict[str, Sequence[str]],
) -> SearchBenchmarkReport:
    """Evaluate adapter-provided ranked slugs without touching production data."""
    fixture.validate()
    if not fixture.cases:
        raise ValueError("Benchmark must contain at least one case")

    reciprocal_ranks = []
    ndcgs = []
    top_k_hits = 0
    zero_results = 0
    for case in fixture.cases:
        ranked = ranked_results.get(case.case_id, ())
        unique_ranked = _unique_ranked_slugs(ranked)
        if not unique_ranked:
            zero_results += 1
        expected = set(case.expected_slugs)
        top_k_hits += int(bool(expected.intersection(unique_ranked[: fixture.top_k])))
        reciprocal_ranks.append(reciprocal_rank(unique_ranked, case.expected_slugs, fixture.cutoff))
        ndcgs.append(ndcg_at_k(unique_ranked, case.expected_slugs, fixture.cutoff))

    count = len(fixture.cases)
    return SearchBenchmarkReport(
        evaluated_cases=count,
        top_k_success=top_k_hits / count,
        mrr_at_cutoff=sum(reciprocal_ranks) / count,
        ndcg_at_cutoff=sum(ndcgs) / count,
        zero_results_rate=zero_results / count,
        cutoff=fixture.cutoff,
        top_k=fixture.top_k,
    )


def _load_ranked_results(path: Path) -> dict[str, Sequence[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_results = payload.get("results", payload)
    if not isinstance(raw_results, dict):
        raise ValueError("Results JSON must be an object keyed by benchmark case ID")
    return {
        str(case_id): tuple(str(slug) for slug in ranked)
        for case_id, ranked in raw_results.items()
        if isinstance(ranked, list)
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument(
        "--check", action="store_true", help="Fail when fixture thresholds are missed"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the offline evaluator against a saved adapter result."""
    args = _build_parser().parse_args(argv)
    fixture = load_search_benchmark(args.fixture)
    report = evaluate_search_benchmark(fixture, _load_ranked_results(args.results))
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    failures = report.threshold_failures(fixture.thresholds)
    if args.check and failures:
        print(f"Benchmark thresholds missed: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
