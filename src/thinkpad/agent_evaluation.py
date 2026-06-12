"""Evaluation helpers for the M8 ThinkPad repair-planning agent."""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.libs.llm.base_llm import BaseLLM
from src.thinkpad.agent import RepairPlanResult, plan_thinkpad_repair
from src.thinkpad.tool_service import ThinkPadToolService

SUPPORTED_AGENT_STATUSES = {"ok", "clarification_required", "not_found", "error"}
SUPPORTED_AGENT_MODES = {"deterministic", "live_retrieval", "live_llm"}


@dataclass(frozen=True)
class ThinkPadAgentGoldenCase:
    """One M8 repair-planning agent golden case."""

    case_id: str
    category: str
    query: str
    expected: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThinkPadAgentGoldenCase:
        case_id = str(data.get("case_id", "")).strip()
        category = str(data.get("category", "")).strip()
        query = str(data.get("query", "")).strip()
        expected = data.get("expected")
        if not case_id:
            raise ValueError("agent golden case missing case_id")
        if not category:
            raise ValueError(f"{case_id}: category is required")
        if not query:
            raise ValueError(f"{case_id}: query is required")
        if not isinstance(expected, dict):
            raise ValueError(f"{case_id}: expected must be an object")
        expected_status = str(expected.get("status", "")).strip()
        if expected_status not in SUPPORTED_AGENT_STATUSES:
            raise ValueError(f"{case_id}: unsupported expected status {expected_status!r}")
        for key in ("required_tools", "manual_ids", "record_types", "identifiers"):
            if key in expected and not isinstance(expected[key], list):
                raise ValueError(f"{case_id}: expected.{key} must be a list")
        return cls(case_id=case_id, category=category, query=query, expected=dict(expected))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class ThinkPadAgentEvalResult:
    """Evaluation result for one M8 agent case."""

    case_id: str
    category: str
    expected_status: str
    actual_status: str
    passed: bool
    metrics: dict[str, float]
    elapsed_ms: float
    failure_reasons: list[str] = field(default_factory=list)
    tool_trace: list[str] = field(default_factory=list)
    result_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class ThinkPadAgentEvalReport:
    """Aggregated M8 agent evaluation report."""

    version: str
    mode: str
    query_count: int
    aggregate_metrics: dict[str, float]
    category_metrics: dict[str, dict[str, float]]
    case_results: list[ThinkPadAgentEvalResult]
    environment: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe report."""

        return {
            "version": self.version,
            "mode": self.mode,
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


def load_thinkpad_agent_golden_set(path: str | Path) -> list[ThinkPadAgentGoldenCase]:
    """Load and validate an M8 agent golden set."""

    golden_path = Path(path)
    if not golden_path.exists():
        raise FileNotFoundError(f"ThinkPad agent golden set not found: {golden_path}")
    with golden_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    raw_cases = data.get("test_cases")
    if not isinstance(raw_cases, list):
        raise ValueError("ThinkPad agent golden set must contain a test_cases list")
    cases = [ThinkPadAgentGoldenCase.from_dict(item) for item in raw_cases]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            duplicates.add(case.case_id)
        seen.add(case.case_id)
    if duplicates:
        raise ValueError(f"Duplicate ThinkPad agent case IDs: {', '.join(sorted(duplicates))}")
    return cases


def evaluate_thinkpad_agent_cases(
    cases: list[ThinkPadAgentGoldenCase],
    service: ThinkPadToolService,
    mode: str = "deterministic",
    collection: str = "thinkpad_m4",
    top_k: int = 5,
    llm: BaseLLM | None = None,
    progress_path: str | Path | None = None,
) -> ThinkPadAgentEvalReport:
    """Evaluate M8 agent cases in deterministic, live retrieval, or live LLM mode."""

    if mode not in SUPPORTED_AGENT_MODES:
        raise ValueError(f"unsupported agent evaluation mode: {mode}")
    if mode == "live_llm" and llm is None:
        raise ValueError("live_llm mode requires an LLM instance")

    results: list[ThinkPadAgentEvalResult] = []
    progress_file = Path(progress_path) if progress_path else None
    if progress_file:
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        progress_file.write_text("", encoding="utf-8")
    for case in cases:
        result = _evaluate_one_case(
            case=case,
            service=service,
            mode=mode,
            collection=collection,
            top_k=top_k,
            llm=llm,
        )
        results.append(result)
        if progress_file:
            with progress_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    aggregate = _aggregate_results(results)
    categories = {
        category: _aggregate_results([result for result in results if result.category == category])
        for category in sorted({result.category for result in results})
    }
    environment = {
        "manual_count": len(service.manuals),
        "mode": mode,
        "failed_case_count": sum(1 for result in results if not result.passed),
        "provider_error_count": sum(
            1 for result in results if result.metrics.get("provider_error_rate") == 1.0
        ),
    }
    return ThinkPadAgentEvalReport(
        version="m8",
        mode=mode,
        query_count=len(cases),
        aggregate_metrics=aggregate,
        category_metrics=categories,
        case_results=results,
        environment=environment,
    )


def _evaluate_one_case(
    case: ThinkPadAgentGoldenCase,
    service: ThinkPadToolService,
    mode: str,
    collection: str,
    top_k: int,
    llm: BaseLLM | None,
) -> ThinkPadAgentEvalResult:
    use_case_llm = bool(mode == "live_llm" and case.expected.get("llm_required", False))
    t0 = time.monotonic()
    try:
        result = plan_thinkpad_repair(
            query=case.query,
            service=service,
            use_llm=use_case_llm,
            llm=llm if use_case_llm else None,
            collection=collection,
            top_k=top_k,
            use_retrieval=mode in {"live_retrieval", "live_llm"},
            require_live_retrieval=mode in {"live_retrieval", "live_llm"},
        )
    except Exception as exc:
        result = _error_result(case.query, str(exc), mode)
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    return _score_agent_response(case, result, elapsed_ms, mode)


def _score_agent_response(
    case: ThinkPadAgentGoldenCase,
    result: RepairPlanResult,
    elapsed_ms: float,
    mode: str,
) -> ThinkPadAgentEvalResult:
    expected = case.expected
    result_dict = result.to_dict()
    expected_status = str(expected["status"])
    actual_status = result.status
    tool_names = [trace.tool for trace in result.tool_trace]
    failure_reasons: list[str] = []
    metrics: dict[str, float] = {
        "final_plan_status_accuracy": 1.0 if actual_status == expected_status else 0.0,
        "provider_error_rate": 1.0 if bool(result.validation.get("provider_error")) else 0.0,
        "unsupported_claim_rate": 1.0 if int(result.validation.get("unsupported_claim_count") or 0) > int(expected.get("max_unsupported_claims", 0)) else 0.0,
        "retrieval_fallback_rate": 1.0 if _has_retrieval_fallback(result) else 0.0,
    }
    if metrics["final_plan_status_accuracy"] == 0.0:
        failure_reasons.append(f"status expected {expected_status}, got {actual_status}")
    if metrics["provider_error_rate"] == 1.0:
        failure_reasons.append("provider error occurred")
    if metrics["unsupported_claim_rate"] == 1.0:
        failure_reasons.append("unsupported claims exceeded expectation")

    if "clarification_needed" in expected:
        expected_clarification = bool(expected["clarification_needed"])
        metrics["clarification_accuracy"] = 1.0 if result.clarification_needed == expected_clarification else 0.0
        if metrics["clarification_accuracy"] == 0.0:
            failure_reasons.append(
                f"clarification expected {expected_clarification}, got {result.clarification_needed}"
            )

    required_tools = [str(tool) for tool in expected.get("required_tools", [])]
    if required_tools:
        metrics["required_tool_coverage"] = _coverage(required_tools, tool_names)
        metrics["trajectory_tool_sequence_accuracy"] = 1.0 if _is_ordered_subsequence(required_tools, tool_names) else 0.0
        if metrics["required_tool_coverage"] < 1.0:
            failure_reasons.append("required tool coverage missing")
        if metrics["trajectory_tool_sequence_accuracy"] == 0.0:
            failure_reasons.append("required tool order missing")

    forbidden_tools = {str(tool) for tool in expected.get("forbidden_tools", [])}
    if forbidden_tools:
        used_forbidden = sorted(forbidden_tools.intersection(tool_names))
        metrics["forbidden_tool_avoidance"] = 0.0 if used_forbidden else 1.0
        if used_forbidden:
            failure_reasons.append(f"forbidden tools used: {', '.join(used_forbidden)}")

    if expected.get("citation_required"):
        metrics["citation_coverage"] = 1.0 if _has_minimum_citation(result.citations) else 0.0
        metrics["citation_accuracy"] = _citation_accuracy(
            citations=result.citations,
            expected_manual_ids=_string_set(expected.get("manual_ids")),
            expected_pages=_int_set(expected.get("pages")),
        )
        if metrics["citation_coverage"] == 0.0:
            failure_reasons.append("minimum citation missing")
        if metrics["citation_accuracy"] == 0.0:
            failure_reasons.append("citation manual/page mismatch")

    expected_record_types = _string_set(expected.get("record_types"))
    if expected_record_types:
        actual_record_types = _record_types(result_dict)
        metrics["record_type_coverage"] = 1.0 if expected_record_types.intersection(actual_record_types) else 0.0
        if metrics["record_type_coverage"] == 0.0:
            failure_reasons.append("expected record type missing")

    identifiers = [str(item).lower() for item in expected.get("identifiers", [])]
    if identifiers:
        flat = json.dumps(result_dict, ensure_ascii=False).lower()
        hits = sum(1 for identifier in identifiers if identifier in flat)
        metrics["evidence_identifier_coverage"] = hits / len(identifiers)
        if metrics["evidence_identifier_coverage"] < 1.0:
            failure_reasons.append("required evidence identifier missing")

    if expected.get("safety_required"):
        has_safety_tool = "get_safety_warnings" in tool_names
        has_warning_record = "warning" in _record_types(result_dict)
        metrics["safety_warning_inclusion"] = 1.0 if has_safety_tool and has_warning_record else 0.0
        if metrics["safety_warning_inclusion"] == 0.0:
            failure_reasons.append("safety warning evidence missing")

    if mode == "live_llm" and expected.get("llm_required", False):
        preserved = result.validation.get("llm_citation_preserved")
        metrics["llm_citation_preservation"] = 1.0 if preserved is True else 0.0
        if metrics["llm_citation_preservation"] == 0.0:
            failure_reasons.append("LLM did not preserve citation labels")

    passed = not failure_reasons
    return ThinkPadAgentEvalResult(
        case_id=case.case_id,
        category=case.category,
        expected_status=expected_status,
        actual_status=actual_status,
        passed=passed,
        metrics=metrics,
        elapsed_ms=elapsed_ms,
        failure_reasons=failure_reasons,
        tool_trace=tool_names,
        result_summary={
            "message": result.message,
            "tool_call_count": len(tool_names),
            "citation_count": len(result.citations),
            "repair_step_count": len(result.repair_plan),
        },
    )


def _error_result(query: str, message: str, mode: str) -> RepairPlanResult:
    from src.thinkpad.agent import EvidenceBundle

    return RepairPlanResult(
        status="error",
        clarification_needed=False,
        query=query,
        message=message,
        request={
            "query": query,
            "collection": "thinkpad_m4",
            "top_k": 5,
            "use_retrieval": mode in {"live_retrieval", "live_llm"},
            "require_live_retrieval": mode in {"live_retrieval", "live_llm"},
            "use_llm": mode == "live_llm",
        },
        evidence_bundle=EvidenceBundle(),
        validation={"provider_error": True, "unsupported_claim_count": 0, "unsupported_claims": []},
    )


def _has_retrieval_fallback(result: RepairPlanResult) -> bool:
    for trace in result.tool_trace:
        if trace.tool == "query_thinkpad_service" and trace.metadata.get("rerank_fallback"):
            return True
    return False


def _coverage(required: list[str], actual: list[str]) -> float:
    if not required:
        return 1.0
    actual_set = set(actual)
    return sum(1 for item in required if item in actual_set) / len(required)


def _is_ordered_subsequence(required: list[str], actual: list[str]) -> bool:
    if not required:
        return True
    index = 0
    for tool in actual:
        if tool == required[index]:
            index += 1
            if index == len(required):
                return True
    return False


def _has_minimum_citation(citations: list[dict[str, Any]]) -> bool:
    return any(citation.get("manual_id") and citation.get("page_start") for citation in citations)


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
        page_ok = any(_citation_matches_page(citation, expected_pages) for citation in citations)
    return 1.0 if manual_ok and page_ok else 0.0


def _citation_matches_page(citation: dict[str, Any], expected_pages: set[int]) -> bool:
    start = citation.get("page_start")
    end = citation.get("page_end") or start
    if start is None:
        return False
    try:
        start_int = int(start)
        end_int = int(end)
    except (TypeError, ValueError):
        return False
    return any(start_int <= page <= end_int for page in expected_pages)


def _record_types(result_dict: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    flat = json.dumps(result_dict, ensure_ascii=False).lower()
    for record_type in (
        "table",
        "fru_procedure",
        "fru_dependency_chain",
        "figure",
        "warning",
        "retrieval",
    ):
        if record_type in flat:
            values.add(record_type)
    return values


def _string_set(value: Any) -> set[str]:
    if not value:
        return set()
    return {str(item).lower() for item in value}


def _int_set(value: Any) -> set[int]:
    if not value:
        return set()
    values: set[int] = set()
    for item in value:
        try:
            values.add(int(item))
        except (TypeError, ValueError):
            continue
    return values


def _aggregate_results(results: list[ThinkPadAgentEvalResult]) -> dict[str, float]:
    metrics: dict[str, list[float]] = {}
    elapsed: list[float] = []
    for result in results:
        elapsed.append(result.elapsed_ms)
        for key, value in result.metrics.items():
            metrics.setdefault(key, []).append(float(value))

    aggregate = {key: statistics.fmean(values) for key, values in metrics.items() if values}
    aggregate["case_count"] = float(len(results))
    aggregate["failed_case_count"] = float(sum(1 for result in results if not result.passed))
    aggregate["passed_case_rate"] = (
        sum(1 for result in results if result.passed) / len(results) if results else 0.0
    )
    aggregate["latency_ms_p50"] = _percentile(elapsed, 50)
    aggregate["latency_ms_p95"] = _percentile(elapsed, 95)
    return aggregate


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percentile / 100) * (len(ordered) - 1))))
    return ordered[index]


def _round_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: round(float(value), 4) for key, value in sorted(metrics.items())}
