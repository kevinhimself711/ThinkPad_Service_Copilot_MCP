from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.thinkpad.agent_evaluation import (
    ThinkPadAgentGoldenCase,
    evaluate_thinkpad_agent_cases,
    load_thinkpad_agent_golden_set,
)
from tests.thinkpad.test_agent import _service_with_records


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


def _case(
    case_id: str,
    query: str,
    required_tools: list[str] | None = None,
    record_types: list[str] | None = None,
    identifiers: list[str] | None = None,
    safety_required: bool = False,
    forbidden_tools: list[str] | None = None,
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
            "record_types": record_types or [],
            "identifiers": identifiers or [],
            "citation_required": True,
            "safety_required": safety_required,
            "max_unsupported_claims": 0,
        },
    }


def _failing_retriever(*args, **kwargs):
    raise RuntimeError("provider unavailable")
