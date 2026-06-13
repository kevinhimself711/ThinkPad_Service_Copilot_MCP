from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.thinkpad.agent import EvidenceBundle, RepairPlanResult, RepairPlanStep
from src.thinkpad.agent_evaluation import (
    ThinkPadAgentGoldenCase,
    _per_step_page_coverage,
    evaluate_thinkpad_agent_cases,
    load_thinkpad_agent_golden_set,
)
from tests.thinkpad.test_agent import FailingLLM, FakeLLM, _llm_json, _service_with_records


def test_load_thinkpad_agent_golden_set_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    path = tmp_path / "agent_cases.json"
    path.write_text(
        json.dumps(
            {
                "test_cases": [
                    _case("duplicate", "21CB battery removal plan"),
                    _case("duplicate", "21CB screw spec M2 x 3"),
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        load_thinkpad_agent_golden_set(path)


def test_agent_evaluator_scores_tool_trajectory_and_citations() -> None:
    service = _service_with_records()
    cases = [
        ThinkPadAgentGoldenCase.from_dict(
            _case(
                "battery_plan",
                "21CB battery removal plan",
                required_tools=[
                    "resolve_thinkpad_model",
                    "get_fru_procedure",
                    "get_fru_dependency_chain",
                    "get_related_diagram",
                    "get_safety_warnings",
                ],
                record_types=["fru_procedure", "fru_dependency_chain", "figure", "warning"],
                identifiers=["1020"],
                safety_required=True,
            )
        )
    ]

    report = evaluate_thinkpad_agent_cases(cases, service)

    result = report.case_results[0]
    assert result.passed is True
    assert report.aggregate_metrics["trajectory_tool_sequence_accuracy"] == 1.0
    assert report.aggregate_metrics["citation_accuracy"] == 1.0
    assert report.aggregate_metrics["safety_warning_inclusion"] == 1.0


def test_agent_evaluator_marks_forbidden_tool_failure() -> None:
    service = _service_with_records()
    cases = [
        ThinkPadAgentGoldenCase.from_dict(
            _case(
                "battery_plan_forbidden",
                "21CB battery removal plan",
                forbidden_tools=["get_fru_procedure"],
            )
        )
    ]

    report = evaluate_thinkpad_agent_cases(cases, service)

    result = report.case_results[0]
    assert result.passed is False
    assert result.metrics["forbidden_tool_avoidance"] == 0.0


def test_agent_evaluator_records_provider_error_from_retriever() -> None:
    service = _service_with_records()
    service._retriever = _failing_retriever  # noqa: SLF001 - test injection
    cases = [ThinkPadAgentGoldenCase.from_dict(_case("live_failure", "21CB battery removal plan"))]

    report = evaluate_thinkpad_agent_cases(cases, service, mode="live_retrieval")

    result = report.case_results[0]
    assert result.passed is False
    assert result.metrics["provider_error_rate"] == 1.0
    assert report.environment["provider_error_count"] == 1


def test_agent_evaluator_recovers_provider_error_but_keeps_raw_metric() -> None:
    service = _service_with_records()
    service._retriever = _empty_retriever  # noqa: SLF001 - test injection
    cases = [
        ThinkPadAgentGoldenCase.from_dict(
            _case(
                "live_llm_recovered",
                "21CB battery removal plan",
                required_tools=[
                    "resolve_thinkpad_model",
                    "get_fru_procedure",
                    "get_fru_dependency_chain",
                    "get_related_diagram",
                    "get_safety_warnings",
                ],
                record_types=["fru_procedure", "fru_dependency_chain", "figure", "warning"],
                identifiers=["1020"],
                safety_required=True,
                llm_required=True,
            )
        )
    ]

    report = evaluate_thinkpad_agent_cases(cases, service, mode="live_llm", llm=FailingLLM())

    result = report.case_results[0]
    assert result.passed is True
    assert result.metrics["provider_error_rate"] == 1.0
    assert result.metrics["provider_clean_rate"] == 0.0
    assert result.metrics["fallback_recovered_rate"] == 1.0
    assert result.metrics["raw_llm_success_rate"] == 0.0
    assert result.result_summary["provider_error_recovered"] is True


def test_agent_evaluator_strict_live_llm_preserves_raw_failure() -> None:
    service = _service_with_records()
    service._retriever = _empty_retriever  # noqa: SLF001 - test injection
    cases = [
        ThinkPadAgentGoldenCase.from_dict(
            _case(
                "strict_llm_failure",
                "21CB battery removal plan",
                required_tools=[
                    "resolve_thinkpad_model",
                    "get_fru_procedure",
                    "get_fru_dependency_chain",
                    "get_related_diagram",
                    "get_safety_warnings",
                ],
                record_types=["fru_procedure", "fru_dependency_chain", "figure", "warning"],
                identifiers=["1020"],
                safety_required=True,
                llm_required=True,
            )
        )
    ]

    llm = FakeLLM("not json")
    report = evaluate_thinkpad_agent_cases(
        cases,
        service,
        mode="live_llm",
        llm=llm,
        strict_live_llm=True,
    )

    result = report.case_results[0]
    assert result.passed is False
    assert llm.calls == 1
    assert result.metrics["raw_llm_success_rate"] == 0.0
    assert result.metrics["fallback_recovered_rate"] == 0.0
    assert "strict live LLM raw output failed" in result.failure_reasons


def test_agent_evaluator_strict_citation_allows_extra_cited_evidence_steps() -> None:
    service = _service_with_records()
    cases = [
        ThinkPadAgentGoldenCase.from_dict(
            _case(
                "strict_citation_extra_evidence",
                "21CB battery removal plan",
                required_tools=[
                    "resolve_thinkpad_model",
                    "get_fru_procedure",
                    "get_fru_dependency_chain",
                    "get_related_diagram",
                    "get_safety_warnings",
                ],
                record_types=["fru_procedure"],
                identifiers=["1020"],
                safety_required=False,
            )
        )
    ]

    report = evaluate_thinkpad_agent_cases(cases, service, strict_citation=True)

    result = report.case_results[0]
    assert result.passed is True
    assert result.metrics["all_step_citation_coverage"] == 1.0
    assert result.metrics["per_step_citation_validity"] == 1.0
    assert result.metrics["required_record_type_coverage"] == 1.0
    assert result.metrics["strict_citation_accuracy"] == 1.0


def test_agent_evaluator_strict_citation_fails_missing_required_page() -> None:
    service = _service_with_records()
    cases = [
        ThinkPadAgentGoldenCase.from_dict(
            _case(
                "strict_citation_page_failure",
                "21CB battery removal plan",
                required_tools=[
                    "resolve_thinkpad_model",
                    "get_fru_procedure",
                    "get_fru_dependency_chain",
                    "get_related_diagram",
                    "get_safety_warnings",
                ],
                record_types=["fru_procedure"],
                pages=[999],
                identifiers=["1020"],
                safety_required=False,
            )
        )
    ]

    report = evaluate_thinkpad_agent_cases(cases, service, strict_citation=True)

    result = report.case_results[0]
    assert result.passed is False
    assert result.metrics["per_step_citation_validity"] == 1.0
    assert result.metrics["required_record_type_coverage"] == 1.0
    assert result.metrics["required_evidence_coverage"] < 1.0
    assert result.metrics["strict_citation_accuracy"] == 0.0
    assert "required citation manual/page/record coverage missing" in result.failure_reasons


def test_per_step_page_coverage_scores_only_fru_procedure_steps() -> None:
    result = RepairPlanResult(
        status="ok",
        clarification_needed=False,
        query="battery removal",
        message="ok",
        request={},
        evidence_bundle=EvidenceBundle(),
        repair_plan=[
            _plan_step("step_01", "fru_procedure", 70),
            _plan_step("step_02", "fru_procedure", 72),
            _plan_step("step_03", "warning", 5),
            _plan_step("step_04", "figure", 99),
        ],
        citations=[
            {"manual_id": "manual_a", "page_start": 70},
            {"manual_id": "manual_a", "page_start": 72},
            {"manual_id": "manual_a", "page_start": 5},
            {"manual_id": "manual_a", "page_start": 99},
        ],
    )

    assert _per_step_page_coverage(result, {70, 71}) == 0.5


def test_agent_evaluator_raw_live_llm_success_metric() -> None:
    service = _service_with_records()
    service._retriever = _empty_retriever  # noqa: SLF001 - test injection
    cases = [
        ThinkPadAgentGoldenCase.from_dict(
            _case(
                "raw_live_llm_success",
                "21CB battery removal plan",
                required_tools=[
                    "resolve_thinkpad_model",
                    "get_fru_procedure",
                    "get_fru_dependency_chain",
                    "get_related_diagram",
                    "get_safety_warnings",
                ],
                record_types=["fru_procedure", "fru_dependency_chain", "figure", "warning"],
                identifiers=["1020"],
                safety_required=True,
                llm_required=True,
            )
        )
    ]

    report = evaluate_thinkpad_agent_cases(
        cases,
        service,
        mode="live_llm",
        llm=FakeLLM(_llm_json("Use cited battery evidence.", extra_citations=True)),
        strict_live_llm=True,
    )

    result = report.case_results[0]
    assert result.passed is True
    assert result.metrics["raw_llm_success_rate"] == 1.0
    assert result.metrics["fallback_recovered_rate"] == 0.0


def _case(
    case_id: str,
    query: str,
    required_tools: list[str] | None = None,
    record_types: list[str] | None = None,
    identifiers: list[str] | None = None,
    safety_required: bool = False,
    forbidden_tools: list[str] | None = None,
    llm_required: bool = False,
    pages: list[int] | None = None,
):
    return {
        "case_id": case_id,
        "category": "agent_test",
        "query": query,
        "expected": {
            "status": "ok",
            "clarification_needed": False,
            "required_tools": required_tools or ["resolve_thinkpad_model"],
            "forbidden_tools": forbidden_tools or [],
            "manual_ids": ["thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm"],
            "pages": pages or [],
            "record_types": record_types or [],
            "identifiers": identifiers or [],
            "citation_required": True,
            "safety_required": safety_required,
            "max_unsupported_claims": 0,
            "llm_required": llm_required,
        },
    }


def _plan_step(step_id: str, evidence_type: str, page: int) -> RepairPlanStep:
    return RepairPlanStep(
        step_id=step_id,
        title=step_id,
        action="Synthetic action",
        evidence_type=evidence_type,
        citations=[{"manual_id": "manual_a", "page_start": page}],
    )


def _failing_retriever(*args, **kwargs):
    raise RuntimeError("provider unavailable")


class _EmptyRetrievalResponse:
    def to_dict(self):
        return {
            "clarification_needed": False,
            "model_resolution": {},
            "reason": "",
            "results": [],
            "domain_rerank": [],
            "rerank_fallback": False,
        }


def _empty_retriever(*args, **kwargs):
    return _EmptyRetrievalResponse()
