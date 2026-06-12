"""ThinkPad-specific evaluation helpers for M6.

The generic upstream evaluator scores chunk-id retrieval. ThinkPad service
queries also need domain checks for model/manual selection, record type,
citations, clarification behavior, and exact identifiers.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.thinkpad.tool_service import ThinkPadToolService

SUPPORTED_TOOLS = {
    "list_supported_models",
    "resolve_thinkpad_model",
    "query_thinkpad_service",
    "lookup_error_code",
    "get_fru_procedure",
    "get_fru_dependency_chain",
    "get_screw_spec",
    "get_related_diagram",
    "get_safety_warnings",
}
SUPPORTED_STATUSES = {"ok", "clarification_required", "not_found", "error", "skipped"}
TOP_K_TOOLS = {
    "lookup_error_code",
    "get_fru_procedure",
    "get_screw_spec",
    "get_related_diagram",
    "get_safety_warnings",
}


@dataclass(frozen=True)
class ThinkPadGoldenCase:
    """One ThinkPad golden evaluation case."""

    case_id: str
    category: str
    tool: str
    input: dict[str, Any]
    expected: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThinkPadGoldenCase:
        """Create and validate a golden case from JSON data."""

        case_id = str(data.get("case_id", "")).strip()
        category = str(data.get("category", "")).strip()
        tool = str(data.get("tool", "")).strip()
        case_input = data.get("input")
        expected = data.get("expected")

        if not case_id:
            raise ValueError("golden case missing case_id")
        if not category:
            raise ValueError(f"{case_id}: category is required")
        if tool not in SUPPORTED_TOOLS:
            raise ValueError(f"{case_id}: unsupported tool {tool!r}")
        if not isinstance(case_input, dict):
            raise ValueError(f"{case_id}: input must be an object")
        if not isinstance(expected, dict):
            raise ValueError(f"{case_id}: expected must be an object")

        expected_status = str(expected.get("status", "")).strip()
        if expected_status not in SUPPORTED_STATUSES:
            raise ValueError(f"{case_id}: unsupported expected status {expected_status!r}")

        return cls(
            case_id=case_id,
            category=category,
            tool=tool,
            input=dict(case_input),
            expected=dict(expected),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class ThinkPadEvalResult:
    """Evaluation result for one ThinkPad golden case."""

    case_id: str
    category: str
    tool: str
    expected_status: str
    actual_status: str
    passed: bool
    skipped: bool
    metrics: dict[str, float]
    elapsed_ms: float
    failure_reasons: list[str] = field(default_factory=list)
    result_count: int = 0
    citations: list[dict[str, Any]] = field(default_factory=list)
    top_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class ThinkPadEvalReport:
    """Aggregated M6 evaluation report."""

    version: str
    collection: str
    top_k: int
    query_count: int
    aggregate_metrics: dict[str, float]
    category_metrics: dict[str, dict[str, float]]
    case_results: list[ThinkPadEvalResult]
    environment: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe report."""

        return {
            "version": self.version,
            "collection": self.collection,
            "top_k": self.top_k,
            "query_count": self.query_count,
            "aggregate_metrics": _round_metrics(self.aggregate_metrics),
            "category_metrics": {
                category: _round_metrics(metrics)
                for category, metrics in sorted(self.category_metrics.items())
            },
            "case_results": [result.to_dict() for result in self.case_results],
            "environment": dict(self.environment),
        }

    def to_json(self) -> str:
        """Return deterministic JSON."""

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def load_thinkpad_golden_set(path: str | Path) -> list[ThinkPadGoldenCase]:
    """Load and validate a ThinkPad M6 golden set."""

    golden_path = Path(path)
    if not golden_path.exists():
        raise FileNotFoundError(f"ThinkPad golden set not found: {golden_path}")

    with golden_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    raw_cases = data.get("test_cases")
    if not isinstance(raw_cases, list):
        raise ValueError("ThinkPad golden set must contain a test_cases list")

    cases = [ThinkPadGoldenCase.from_dict(item) for item in raw_cases]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            duplicates.add(case.case_id)
        seen.add(case.case_id)
    if duplicates:
        raise ValueError(f"Duplicate ThinkPad golden case IDs: {', '.join(sorted(duplicates))}")
    return cases


def evaluate_thinkpad_cases(
    cases: list[ThinkPadGoldenCase],
    service: ThinkPadToolService,
    collection: str = "thinkpad_m4",
    top_k: int = 5,
    run_live_retrieval: bool = False,
    live_retrieval_required: bool = False,
) -> ThinkPadEvalReport:
    """Evaluate ThinkPad golden cases against the M5 tool service."""

    results: list[ThinkPadEvalResult] = []
    for case in cases:
        results.append(
            _evaluate_one_case(
                case=case,
                service=service,
                collection=collection,
                top_k=top_k,
                run_live_retrieval=run_live_retrieval,
                live_retrieval_required=live_retrieval_required,
            )
        )

    aggregate = _aggregate_results(results)
    categories = {
        category: _aggregate_results([result for result in results if result.category == category])
        for category in sorted({result.category for result in results})
    }
    environment = {
        "live_retrieval_required": live_retrieval_required,
        "live_retrieval_available": run_live_retrieval,
        "manual_count": len(service.manuals),
        "skipped_case_count": sum(1 for result in results if result.skipped),
        "failed_case_count": sum(1 for result in results if not result.passed and not result.skipped),
    }
    return ThinkPadEvalReport(
        version=_report_version(cases),
        collection=collection,
        top_k=top_k,
        query_count=len(cases),
        aggregate_metrics=aggregate,
        category_metrics=categories,
        case_results=results,
        environment=environment,
    )


def _evaluate_one_case(
    case: ThinkPadGoldenCase,
    service: ThinkPadToolService,
    collection: str,
    top_k: int,
    run_live_retrieval: bool,
    live_retrieval_required: bool,
) -> ThinkPadEvalResult:
    if case.tool == "query_thinkpad_service" and not run_live_retrieval:
        return _skipped_result(case, "live retrieval not enabled")

    t0 = time.monotonic()
    try:
        response = _call_tool(case, service, collection=collection, top_k=top_k)
    except Exception as exc:
        response = {
            "tool": case.tool,
            "status": "error",
            "clarification_needed": False,
            "message": str(exc),
            "results": [],
            "citations": [],
            "metadata": {},
        }
    elapsed_ms = (time.monotonic() - t0) * 1000.0

    if (
        live_retrieval_required
        and case.tool == "query_thinkpad_service"
        and response.get("status") == "error"
    ):
        response["message"] = f"live retrieval required but failed: {response.get('message', '')}"

    return _score_response(case, response, elapsed_ms)


def _call_tool(
    case: ThinkPadGoldenCase,
    service: ThinkPadToolService,
    collection: str,
    top_k: int,
) -> dict[str, Any]:
    params = dict(case.input)
    if case.tool == "query_thinkpad_service":
        params.setdefault("collection", collection)
        params.setdefault("top_k", top_k)
    elif case.tool in TOP_K_TOOLS:
        params.setdefault("top_k", top_k)
    method = getattr(service, case.tool)
    response = method(**params)
    if not isinstance(response, dict):
        raise TypeError(f"{case.tool} returned {type(response).__name__}, expected dict")
    return response


def _score_response(
    case: ThinkPadGoldenCase,
    response: dict[str, Any],
    elapsed_ms: float,
) -> ThinkPadEvalResult:
    expected = case.expected
    expected_status = str(expected["status"])
    actual_status = str(response.get("status", "error"))
    results = list(response.get("results") or [])
    citations = list(response.get("citations") or [])
    metrics: dict[str, float] = {
        "tool_status_accuracy": 1.0 if actual_status == expected_status else 0.0,
        "empty_unexpected_result_rate": (
            1.0 if expected_status == "ok" and actual_status == "ok" and not results else 0.0
        ),
    }
    failure_reasons: list[str] = []
    if metrics["tool_status_accuracy"] == 0.0:
        failure_reasons.append(f"status expected {expected_status}, got {actual_status}")
    if metrics["empty_unexpected_result_rate"] == 1.0:
        failure_reasons.append("expected non-empty results")

    if "clarification_needed" in expected:
        expected_clarification = bool(expected["clarification_needed"])
        actual_clarification = bool(response.get("clarification_needed"))
        metrics["clarification_accuracy"] = 1.0 if actual_clarification == expected_clarification else 0.0
        if metrics["clarification_accuracy"] == 0.0:
            failure_reasons.append(
                f"clarification expected {expected_clarification}, got {actual_clarification}"
            )

    _add_rank_metrics(
        metrics=metrics,
        failure_reasons=failure_reasons,
        prefix="manual",
        expected_values=_string_set(expected.get("manual_ids")),
        ranked_values=[_manual_id_for_result(result) for result in results],
    )
    _add_rank_metrics(
        metrics=metrics,
        failure_reasons=failure_reasons,
        prefix="record_type",
        expected_values=_string_set(expected.get("record_types")),
        ranked_values=[_record_type_for_result(result) for result in results],
    )

    expected_identifiers = [str(item).lower() for item in expected.get("identifiers", [])]
    if expected_identifiers:
        flat_response = _flatten_text(response)
        identifier_hit = any(identifier in flat_response for identifier in expected_identifiers)
        metrics["identifier_hit_at_k"] = 1.0 if identifier_hit else 0.0
        if not identifier_hit:
            failure_reasons.append(
                f"expected identifier missing: {', '.join(expected_identifiers)}"
            )

    if bool(expected.get("citation_required")):
        citation_coverage = _citation_coverage(results=results, citations=citations)
        citation_accuracy = _citation_accuracy(
            citations=citations,
            expected_manual_ids=_string_set(expected.get("manual_ids")),
            expected_pages=_int_set(expected.get("pages")),
        )
        metrics["citation_coverage"] = citation_coverage
        metrics["citation_accuracy"] = citation_accuracy
        if citation_coverage == 0.0:
            failure_reasons.append("missing minimum citation fields")
        if citation_accuracy == 0.0:
            failure_reasons.append("citation did not match expected manual/page")

    passed = not failure_reasons
    return ThinkPadEvalResult(
        case_id=case.case_id,
        category=case.category,
        tool=case.tool,
        expected_status=expected_status,
        actual_status=actual_status,
        passed=passed,
        skipped=False,
        metrics=metrics,
        elapsed_ms=elapsed_ms,
        failure_reasons=failure_reasons,
        result_count=len(results),
        citations=_summarize_citations(citations),
        top_results=[_summarize_result(result, rank) for rank, result in enumerate(results[:5], start=1)],
    )


def _skipped_result(case: ThinkPadGoldenCase, reason: str) -> ThinkPadEvalResult:
    return ThinkPadEvalResult(
        case_id=case.case_id,
        category=case.category,
        tool=case.tool,
        expected_status=str(case.expected["status"]),
        actual_status="skipped",
        passed=False,
        skipped=True,
        metrics={},
        elapsed_ms=0.0,
        failure_reasons=[reason],
        result_count=0,
    )


def _add_rank_metrics(
    metrics: dict[str, float],
    failure_reasons: list[str],
    prefix: str,
    expected_values: set[str],
    ranked_values: list[str | None],
) -> None:
    if not expected_values:
        return
    rank = _first_rank(expected_values, ranked_values)
    metrics[f"{prefix}_hit_at_k"] = 1.0 if rank is not None else 0.0
    metrics[f"{prefix}_mrr"] = (1.0 / rank) if rank is not None else 0.0
    if rank is None:
        failure_reasons.append(f"{prefix} hit missing")


def _first_rank(expected: set[str], ranked_values: list[str | None]) -> int | None:
    for rank, value in enumerate(ranked_values, start=1):
        if value and value.lower() in expected:
            return rank
    return None


def _manual_id_for_result(result: dict[str, Any]) -> str | None:
    citation = result.get("citation") if isinstance(result.get("citation"), dict) else {}
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    value = result.get("manual_id") or citation.get("manual_id") or metadata.get("manual_id")
    return str(value).lower() if value else None


def _record_type_for_result(result: dict[str, Any]) -> str | None:
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    value = result.get("record_type") or metadata.get("record_type")
    return str(value).lower() if value else None


def _citation_coverage(results: list[dict[str, Any]], citations: list[dict[str, Any]]) -> float:
    if results:
        result_citations = [
            result.get("citation")
            for result in results
            if isinstance(result.get("citation"), dict)
        ]
        if len(result_citations) != len(results):
            return 0.0
        return 1.0 if all(_has_minimum_citation(citation) for citation in result_citations) else 0.0
    return 1.0 if citations and all(_has_minimum_citation(citation) for citation in citations) else 0.0


def _citation_accuracy(
    citations: list[dict[str, Any]],
    expected_manual_ids: set[str],
    expected_pages: set[int],
) -> float:
    if not citations:
        return 0.0
    manual_ok = True
    page_ok = True
    if expected_manual_ids:
        manual_ok = any(str(citation.get("manual_id", "")).lower() in expected_manual_ids for citation in citations)
    if expected_pages:
        page_ok = any(_page_in_expected(citation, expected_pages) for citation in citations)
    return 1.0 if manual_ok and page_ok else 0.0


def _page_in_expected(citation: dict[str, Any], expected_pages: set[int]) -> bool:
    page_start = citation.get("page_start")
    page_end = citation.get("page_end") or page_start
    try:
        start = int(page_start)
        end = int(page_end)
    except (TypeError, ValueError):
        return False
    return any(start <= page <= end for page in expected_pages)


def _has_minimum_citation(citation: dict[str, Any]) -> bool:
    return bool(citation.get("manual_id") and citation.get("source_url") and citation.get("page_start"))


def _summarize_result(result: dict[str, Any], rank: int) -> dict[str, Any]:
    citation = result.get("citation") if isinstance(result.get("citation"), dict) else {}
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    return {
        "rank": rank,
        "manual_id": _manual_id_for_result(result),
        "record_type": _record_type_for_result(result),
        "table_type": result.get("table_type") or metadata.get("table_type"),
        "record_id": result.get("record_id") or result.get("chunk_id"),
        "procedure_id": result.get("procedure_id"),
        "fru_id": result.get("fru_id") or metadata.get("fru_id"),
        "image_id": result.get("image_id"),
        "warning_id": result.get("warning_id"),
        "score": result.get("score"),
        "page_start": citation.get("page_start"),
        "section_id": citation.get("section_id"),
    }


def _summarize_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "manual_id": citation.get("manual_id"),
            "source_url": citation.get("source_url"),
            "page_start": citation.get("page_start"),
            "page_end": citation.get("page_end"),
            "section": citation.get("section"),
            "section_id": citation.get("section_id"),
        }
        for citation in citations[:10]
    ]


def _aggregate_results(results: list[ThinkPadEvalResult]) -> dict[str, float]:
    metrics: dict[str, list[float]] = {}
    latencies = [result.elapsed_ms for result in results if not result.skipped]
    for result in results:
        if result.skipped:
            continue
        for name, value in result.metrics.items():
            metrics.setdefault(name, []).append(float(value))

    aggregate = {
        name: sum(values) / len(values)
        for name, values in metrics.items()
        if values
    }
    aggregate["case_count"] = float(len(results))
    aggregate["evaluated_case_count"] = float(sum(1 for result in results if not result.skipped))
    aggregate["skipped_case_count"] = float(sum(1 for result in results if result.skipped))
    aggregate["passed_case_rate"] = (
        sum(1 for result in results if result.passed) / len(results) if results else 0.0
    )
    aggregate["failed_case_count"] = float(sum(1 for result in results if not result.passed and not result.skipped))
    aggregate["latency_ms_p50"] = _percentile(latencies, 50)
    aggregate["latency_ms_p95"] = _percentile(latencies, 95)
    return aggregate


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * percentile / 100
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return float(sorted_values[lower])
    fraction = index - lower
    return float(sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction)


def _round_metrics(metrics: dict[str, float]) -> dict[str, float]:
    rounded: dict[str, float] = {}
    for key, value in metrics.items():
        rounded[key] = round(float(value), 4)
    return rounded


def _string_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if not isinstance(value, list):
        value = [value]
    return {str(item).lower() for item in value if str(item).strip()}


def _int_set(value: Any) -> set[int]:
    if value is None:
        return set()
    if not isinstance(value, list):
        value = [value]
    result: set[int] = set()
    for item in value:
        try:
            result.add(int(item))
        except (TypeError, ValueError):
            continue
    return result


def _report_version(cases: list[ThinkPadGoldenCase]) -> str:
    if any(case.tool == "get_fru_dependency_chain" for case in cases):
        return "m7"
    return "m6"


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values()).lower()
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value).lower()
    return str(value).lower()
