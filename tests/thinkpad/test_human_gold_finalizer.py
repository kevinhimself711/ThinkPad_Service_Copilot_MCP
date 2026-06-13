from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "thinkpad_finalize_human_gold.py"
    spec = importlib.util.spec_from_file_location("thinkpad_finalize_human_gold", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_finalize_human_gold_uses_markdown_annotations(tmp_path: Path) -> None:
    module = _load_script()
    review_json = _write_review_json(tmp_path)
    review_markdown = _write_review_markdown(tmp_path)
    output = tmp_path / "human_gold.json"
    audit = tmp_path / "audit.json"

    finalized = module.finalize_human_gold(review_json, review_markdown, output, audit)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["version"] == "m8_4_human_gold"
    assert data["review_summary"]["accepted_count"] == 3
    assert data["review_summary"]["rejected_count"] == 1
    assert len(data["test_cases"]) == 3
    assert finalized["audit"]["status_counts"] == {"corrected": 1, "rejected": 1, "verified": 2}

    corrected = _case_by_id(data, "m8_4_positive_corrected")
    assert corrected["expected"]["pages"] == [9, 10]
    assert corrected["human_review"]["candidate_pages"] == [8]
    assert corrected["human_review"]["verified_pages"] == [9, 10]

    negative = _case_by_id(data, "m8_4_negative")
    assert negative["expected"]["status"] == "clarification_required"
    assert negative["expected"]["citation_required"] is False
    assert negative["expected"]["forbidden_tools"] == ["get_fru_procedure"]

    serialized = json.dumps(data, ensure_ascii=False)
    assert "Replace the system board" not in serialized


def test_finalize_human_gold_rejects_positive_case_without_verified_pages(tmp_path: Path) -> None:
    module = _load_script()
    review_json = _write_review_json(tmp_path)
    review_markdown = _write_review_markdown(tmp_path, no_pages_for_positive=True)

    with pytest.raises(ValueError, match="requires verified_pages"):
        module.finalize_human_gold(
            review_json,
            review_markdown,
            tmp_path / "human_gold.json",
            tmp_path / "audit.json",
        )


def test_finalize_human_gold_rejects_pending_annotations(tmp_path: Path) -> None:
    module = _load_script()
    review_json = _write_review_json(tmp_path)
    review_markdown = _write_review_markdown(tmp_path, pending=True)

    with pytest.raises(ValueError, match="pending candidates"):
        module.finalize_human_gold(
            review_json,
            review_markdown,
            tmp_path / "human_gold.json",
            tmp_path / "audit.json",
        )


def _case_by_id(data: dict, case_id: str) -> dict:
    for item in data["test_cases"]:
        if item["case_id"] == case_id:
            return item
    raise AssertionError(f"missing case {case_id}")


def _write_review_json(tmp_path: Path) -> Path:
    candidates = [
        {
            "case_id": "m8_4a_positive_verified",
            "category": "fru_procedure",
            "query": "ThinkPad X battery removal plan",
            "expected_status": "ok",
            "manual_id": "manual_a",
            "candidate_pages": [1, 2],
            "record_type": "fru_procedure",
            "identifier": "1010",
            "required_tools": ["resolve_thinkpad_model", "get_fru_procedure"],
            "pdf_local_path": "data/manuals/manual_a.pdf",
            "source_record_id": "manual_a_fru_1010",
            "source_record_kind": "fru_procedure",
            "review_status": "pending",
            "verified_pages": [],
            "reviewer_notes": "",
        },
        {
            "case_id": "m8_4a_positive_corrected",
            "category": "table",
            "query": "ThinkPad X error code 0177",
            "expected_status": "ok",
            "manual_id": "manual_b",
            "candidate_pages": [8],
            "record_type": "table",
            "identifier": "0177",
            "required_tools": ["resolve_thinkpad_model", "lookup_error_code"],
            "pdf_local_path": "data/manuals/manual_b.pdf",
            "source_record_id": "manual_b_table_0177",
            "source_record_kind": "table:error_code",
            "review_status": "pending",
            "verified_pages": [],
            "reviewer_notes": "",
        },
        {
            "case_id": "m8_4a_rejected",
            "category": "supporting_evidence",
            "query": "ThinkPad X battery warning",
            "expected_status": "ok",
            "manual_id": "manual_c",
            "candidate_pages": [3],
            "record_type": "warning",
            "identifier": "battery",
            "required_tools": ["resolve_thinkpad_model", "get_safety_warnings"],
            "pdf_local_path": "data/manuals/manual_c.pdf",
            "source_record_id": "manual_c_p003_warning",
            "source_record_kind": "warning",
            "review_status": "pending",
            "verified_pages": [],
            "reviewer_notes": "",
        },
        {
            "case_id": "m8_4a_negative",
            "category": "negative",
            "query": "X1 Carbon battery removal plan",
            "expected_status": "clarification_required",
            "manual_id": None,
            "candidate_pages": [],
            "record_type": None,
            "identifier": "generation_required",
            "required_tools": ["resolve_thinkpad_model"],
            "pdf_local_path": None,
            "source_record_id": None,
            "source_record_kind": "negative:model_ambiguity",
            "review_status": "pending",
            "verified_pages": [],
            "reviewer_notes": "",
        },
    ]
    path = tmp_path / "review.json"
    path.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
    return path


def _write_review_markdown(
    tmp_path: Path,
    no_pages_for_positive: bool = False,
    pending: bool = False,
) -> Path:
    first_status = "pending" if pending else "verified"
    first_pages = "[]" if no_pages_for_positive else "[1, 2]"
    content = f"""# Review

## 1. m8_4a_positive_verified

- Review status: `{first_status}`
- Verified pages: `{first_pages}`
- Reviewer notes: ``

## 2. m8_4a_positive_corrected

- Review status: `corrected`
- Verified pages: `[9, 10]`
- Reviewer notes: `corrected page range`

## 3. m8_4a_rejected

- Review status: `rejected`
- Verified pages: `[]`
- Reviewer notes: `false positive`

## 4. m8_4a_negative

- Review status: `verified`
- Verified pages: `[]`
- Reviewer notes: `ambiguous model`
"""
    path = tmp_path / "review.md"
    path.write_text(content, encoding="utf-8")
    return path
