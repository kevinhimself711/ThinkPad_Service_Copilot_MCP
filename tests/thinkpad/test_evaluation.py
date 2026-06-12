from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.thinkpad.evaluation import (
    ThinkPadGoldenCase,
    evaluate_thinkpad_cases,
    load_thinkpad_golden_set,
)


def _write_golden(path: Path, cases: list[dict[str, Any]]) -> Path:
    path.write_text(json.dumps({"test_cases": cases}, ensure_ascii=False), encoding="utf-8")
    return path


def _case(
    case_id: str = "case_1",
    tool: str = "resolve_thinkpad_model",
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": "unit",
        "tool": tool,
        "input": {"query": "21CB"},
        "expected": expected or {"status": "ok"},
    }


class _FakeManualsService:
    manuals = [object(), object()]

    def resolve_thinkpad_model(self, query: str) -> dict[str, Any]:
        if query == "ambiguous":
            return {
                "tool": "resolve_thinkpad_model",
                "status": "clarification_required",
                "clarification_needed": True,
                "message": "generation_required",
                "results": [],
                "citations": [],
                "metadata": {},
            }
        return {
            "tool": "resolve_thinkpad_model",
            "status": "ok",
            "clarification_needed": False,
            "message": "",
            "results": [
                {
                    "manual_id": "wrong_manual",
                    "record_type": "candidate",
                },
                {
                    "manual_id": "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
                    "record_type": "candidate",
                    "machine_types": ["21CB"],
                },
            ],
            "citations": [],
            "metadata": {},
        }

    def query_thinkpad_service(
        self,
        query: str,
        top_k: int = 5,
        collection: str = "thinkpad_m4",
    ) -> dict[str, Any]:
        return {
            "tool": "query_thinkpad_service",
            "status": "ok",
            "clarification_needed": False,
            "message": "",
            "results": [
                {
                    "chunk_id": "warning::1",
                    "record_type": "warning",
                    "metadata": {"record_type": "warning", "manual_id": "wrong_manual"},
                    "citation": {
                        "manual_id": "wrong_manual",
                        "source_url": "https://download.lenovo.com/mock.pdf",
                        "page_start": 2,
                        "page_end": 2,
                    },
                },
                {
                    "chunk_id": "fru::1020",
                    "record_type": "fru_procedure",
                    "metadata": {
                        "record_type": "fru_procedure",
                        "manual_id": "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
                    },
                    "citation": {
                        "manual_id": "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
                        "source_url": "https://download.lenovo.com/mock.pdf",
                        "page_start": 72,
                        "page_end": 73,
                        "section_id": "1020",
                    },
                    "text": "built-in battery 1020",
                },
            ],
            "citations": [
                {
                    "manual_id": "wrong_manual",
                    "source_url": "https://download.lenovo.com/mock.pdf",
                    "page_start": 2,
                    "page_end": 2,
                },
                {
                    "manual_id": "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
                    "source_url": "https://download.lenovo.com/mock.pdf",
                    "page_start": 72,
                    "page_end": 73,
                    "section_id": "1020",
                },
            ],
            "metadata": {"collection": collection, "top_k": top_k},
        }


def test_load_thinkpad_golden_set_accepts_valid_cases(tmp_path: Path) -> None:
    path = _write_golden(tmp_path / "golden.json", [_case()])

    cases = load_thinkpad_golden_set(path)

    assert len(cases) == 1
    assert cases[0].case_id == "case_1"


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (lambda item: item.pop("case_id"), "case_id"),
        (lambda item: item.__setitem__("tool", "bad_tool"), "unsupported tool"),
        (lambda item: item["expected"].__setitem__("status", "maybe"), "unsupported expected status"),
    ],
)
def test_load_thinkpad_golden_set_rejects_invalid_cases(
    tmp_path: Path,
    mutator,
    match: str,
) -> None:
    item = _case()
    mutator(item)
    path = _write_golden(tmp_path / "golden.json", [item])

    with pytest.raises(ValueError, match=match):
        load_thinkpad_golden_set(path)


def test_load_thinkpad_golden_set_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    path = _write_golden(tmp_path / "golden.json", [_case(), _case()])

    with pytest.raises(ValueError, match="Duplicate"):
        load_thinkpad_golden_set(path)


def test_evaluate_thinkpad_cases_computes_rank_and_citation_metrics() -> None:
    cases = [
        ThinkPadGoldenCase.from_dict(
            {
                "case_id": "retrieval_case",
                "category": "live_retrieval",
                "tool": "query_thinkpad_service",
                "input": {"query": "21CB battery removal"},
                "expected": {
                    "status": "ok",
                    "manual_ids": ["thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm"],
                    "record_types": ["fru_procedure"],
                    "identifiers": ["1020"],
                    "citation_required": True,
                    "pages": [72],
                },
            }
        )
    ]

    report = evaluate_thinkpad_cases(
        cases=cases,
        service=_FakeManualsService(),  # type: ignore[arg-type]
        run_live_retrieval=True,
    )

    result = report.case_results[0]
    assert result.metrics["manual_hit_at_k"] == 1.0
    assert result.metrics["manual_mrr"] == 0.5
    assert result.metrics["record_type_hit_at_k"] == 1.0
    assert result.metrics["record_type_mrr"] == 0.5
    assert result.metrics["citation_coverage"] == 1.0
    assert result.metrics["citation_accuracy"] == 1.0
    assert result.metrics["identifier_hit_at_k"] == 1.0
    assert report.aggregate_metrics["manual_mrr"] == 0.5


def test_evaluate_thinkpad_cases_skips_live_retrieval_when_disabled() -> None:
    cases = [
        ThinkPadGoldenCase.from_dict(
            {
                "case_id": "retrieval_case",
                "category": "live_retrieval",
                "tool": "query_thinkpad_service",
                "input": {"query": "21CB battery removal"},
                "expected": {"status": "ok"},
            }
        )
    ]

    report = evaluate_thinkpad_cases(
        cases=cases,
        service=_FakeManualsService(),  # type: ignore[arg-type]
        run_live_retrieval=False,
    )

    assert report.case_results[0].skipped is True
    assert report.case_results[0].actual_status == "skipped"
    assert report.aggregate_metrics["skipped_case_count"] == 1.0


def test_evaluate_thinkpad_cases_scores_clarification() -> None:
    cases = [
        ThinkPadGoldenCase.from_dict(
            {
                "case_id": "ambiguous",
                "category": "model_ambiguity",
                "tool": "resolve_thinkpad_model",
                "input": {"query": "ambiguous"},
                "expected": {
                    "status": "clarification_required",
                    "clarification_needed": True,
                    "identifiers": ["generation_required"],
                },
            }
        )
    ]

    report = evaluate_thinkpad_cases(cases=cases, service=_FakeManualsService())  # type: ignore[arg-type]

    result = report.case_results[0]
    assert result.passed is True
    assert result.metrics["tool_status_accuracy"] == 1.0
    assert result.metrics["clarification_accuracy"] == 1.0
    assert result.metrics["identifier_hit_at_k"] == 1.0


def test_eval_report_serializes_json_safe_dict() -> None:
    report = evaluate_thinkpad_cases(
        cases=[
            ThinkPadGoldenCase.from_dict(
                {
                    "case_id": "model_case",
                    "category": "model_resolution",
                    "tool": "resolve_thinkpad_model",
                    "input": {"query": "21CB"},
                    "expected": {
                        "status": "ok",
                        "manual_ids": ["thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm"],
                    },
                }
            )
        ],
        service=_FakeManualsService(),  # type: ignore[arg-type]
    )

    data = report.to_dict()

    assert data["version"] == "m6"
    assert data["query_count"] == 1
    assert data["case_results"][0]["case_id"] == "model_case"
    json.dumps(data)
