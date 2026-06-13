#!/usr/bin/env python
"""Finalize M8.4 human-reviewed candidates into a committed golden set.

The M8.4a review JSON is generated data and may remain pending. The human
review happens in the local Markdown pack, so this script treats Markdown
annotations as authoritative and merges them back onto the original candidate
metadata. It writes only copyright-light identifiers, pages, and expectations.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ACCEPTED_STATUSES = {"verified", "corrected"}
_ALLOWED_STATUSES = _ACCEPTED_STATUSES | {"pending", "rejected"}
_HEADING_RE = re.compile(r"^##\s+\d+\.\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class HumanReviewAnnotation:
    """Human annotation parsed from the local Markdown review pack."""

    case_id: str
    review_status: str
    verified_pages: list[int]
    reviewer_notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize M8.4 human-reviewed ThinkPad gold cases.")
    parser.add_argument("--review-json", default="data/eval/m8_4_human_gold_review.json")
    parser.add_argument("--review-markdown", default="data/eval/m8_4_human_gold_review.md")
    parser.add_argument("--output", default="tests/fixtures/thinkpad_m8_4_human_gold_set.json")
    parser.add_argument("--audit-output", default="data/eval/m8_4_human_gold_finalize_audit.json")
    return parser.parse_args()


def main() -> int:
    _configure_windows_stdio()
    args = parse_args()
    try:
        finalized = finalize_human_gold(
            review_json=args.review_json,
            review_markdown=args.review_markdown,
            output=args.output,
            audit_output=args.audit_output,
        )
    except Exception as exc:
        print(f"M8.4 human gold finalization failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(finalized["audit"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _configure_windows_stdio() -> None:
    if sys.platform != "win32":
        return
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def finalize_human_gold(
    review_json: str | Path,
    review_markdown: str | Path,
    output: str | Path,
    audit_output: str | Path | None = None,
) -> dict[str, Any]:
    """Build the committed human gold fixture from reviewed M8.4a candidates."""

    review_data = _read_json(review_json)
    raw_candidates = review_data.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError("review JSON must contain a candidates list")

    annotations = parse_review_markdown(review_markdown)
    candidates = [_merge_annotation(candidate, annotations) for candidate in raw_candidates]
    pending = [item["case_id"] for item in candidates if item["review_status"] == "pending"]
    if pending:
        raise ValueError(f"review contains pending candidates: {', '.join(pending)}")

    accepted_cases = [_to_agent_gold_case(item) for item in candidates if item["review_status"] in _ACCEPTED_STATUSES]
    fixture = {
        "version": "m8_4_human_gold",
        "source": (
            "Human-reviewed M8.4 ThinkPad agent gold set generated from local M8.4a review annotations. "
            "Contains only copyright-light queries, identifiers, page numbers, and expected evidence constraints; "
            "no Lenovo manual prose is included."
        ),
        "review_summary": _review_summary(candidates, accepted_cases),
        "test_cases": accepted_cases,
    }

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    audit = {
        "version": "m8_4b_finalize_audit",
        "review_json": str(review_json),
        "review_markdown": str(review_markdown),
        "output": str(output_path),
        "candidate_count": len(candidates),
        "accepted_count": len(accepted_cases),
        "skipped_count": len(candidates) - len(accepted_cases),
        "status_counts": dict(sorted(Counter(item["review_status"] for item in candidates).items())),
        "accepted_case_ids": [case["case_id"] for case in accepted_cases],
        "rejected_case_ids": [item["case_id"] for item in candidates if item["review_status"] == "rejected"],
    }
    if audit_output:
        audit_path = Path(audit_output)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(
            json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {"fixture": fixture, "audit": audit}


def parse_review_markdown(path: str | Path) -> dict[str, HumanReviewAnnotation]:
    """Parse review annotations from an M8.4a Markdown review pack."""

    markdown_path = Path(path)
    if not markdown_path.exists():
        raise FileNotFoundError(f"review markdown not found: {markdown_path}")
    text = markdown_path.read_text(encoding="utf-8")
    matches = list(_HEADING_RE.finditer(text))
    annotations: dict[str, HumanReviewAnnotation] = {}
    for index, match in enumerate(matches):
        case_id = match.group(1).strip()
        section_start = match.end()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[section_start:section_end]
        fields = _parse_markdown_fields(section)
        status = str(fields.get("Review status", "pending")).strip().lower()
        if status not in _ALLOWED_STATUSES:
            raise ValueError(f"{case_id}: unsupported review_status {status!r}")
        verified_pages = _parse_page_list(fields.get("Verified pages", "[]"), case_id)
        annotations[case_id] = HumanReviewAnnotation(
            case_id=case_id,
            review_status=status,
            verified_pages=verified_pages,
            reviewer_notes=str(fields.get("Reviewer notes", "")).strip(),
        )
    return annotations


def _parse_markdown_fields(section: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        key, separator, value = stripped[2:].partition(":")
        if not separator:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


def _parse_page_list(raw: str, case_id: str) -> list[int]:
    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError) as exc:
        raise ValueError(f"{case_id}: verified_pages must be a Python/JSON-style list") from exc
    if not isinstance(parsed, list):
        raise ValueError(f"{case_id}: verified_pages must be a list")
    pages: list[int] = []
    for item in parsed:
        try:
            page = int(item)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{case_id}: verified_pages contains non-integer value {item!r}") from exc
        if page < 1:
            raise ValueError(f"{case_id}: verified_pages must be positive")
        pages.append(page)
    return pages


def _read_json(path: str | Path) -> dict[str, Any]:
    json_path = Path(path)
    if not json_path.exists():
        raise FileNotFoundError(f"review JSON not found: {json_path}")
    with json_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("review JSON must be an object")
    return data


def _merge_annotation(
    candidate: dict[str, Any],
    annotations: dict[str, HumanReviewAnnotation],
) -> dict[str, Any]:
    case_id = str(candidate.get("case_id") or "").strip()
    if not case_id:
        raise ValueError("review candidate missing case_id")
    annotation = annotations.get(case_id)
    if annotation is None:
        raise ValueError(f"{case_id}: missing Markdown review annotation")
    merged = dict(candidate)
    merged["review_status"] = annotation.review_status
    merged["verified_pages"] = annotation.verified_pages
    merged["reviewer_notes"] = annotation.reviewer_notes
    return merged


def _to_agent_gold_case(candidate: dict[str, Any]) -> dict[str, Any]:
    expected_status = str(candidate.get("expected_status") or "").strip()
    if expected_status not in {"ok", "clarification_required", "not_found", "error"}:
        raise ValueError(f"{candidate.get('case_id')}: unsupported expected_status {expected_status!r}")

    manual_id = str(candidate.get("manual_id") or "").strip()
    verified_pages = [int(page) for page in candidate.get("verified_pages") or []]
    if expected_status == "ok" and not verified_pages:
        raise ValueError(f"{candidate.get('case_id')}: accepted positive case requires verified_pages")

    record_type = str(candidate.get("record_type") or "").strip()
    identifier = str(candidate.get("identifier") or "").strip()
    category = str(candidate.get("category") or "").strip()
    case_id = str(candidate.get("case_id") or "").strip().replace("m8_4a_", "m8_4_")
    expected = {
        "status": expected_status,
        "clarification_needed": expected_status == "clarification_required",
        "required_tools": list(candidate.get("required_tools") or []),
        "forbidden_tools": ["get_fru_procedure"] if expected_status in {"clarification_required", "not_found"} else [],
        "manual_ids": [manual_id] if manual_id else [],
        "pages": verified_pages,
        "record_types": [record_type] if record_type else [],
        "identifiers": [identifier] if identifier else [],
        "citation_required": expected_status == "ok",
        "safety_required": record_type == "warning",
        "max_unsupported_claims": 0,
        "llm_required": category in {"fru_procedure", "fru_dependency_chain"},
    }
    return {
        "case_id": case_id,
        "category": f"human_{category}" if category else "human_unknown",
        "query": str(candidate.get("query") or "").strip(),
        "expected": expected,
        "human_review": {
            "source_case_id": candidate.get("case_id"),
            "review_status": candidate.get("review_status"),
            "candidate_pages": list(candidate.get("candidate_pages") or []),
            "verified_pages": verified_pages,
            "reviewer_notes": str(candidate.get("reviewer_notes") or ""),
            "source_record_id": candidate.get("source_record_id"),
            "source_record_kind": candidate.get("source_record_kind"),
        },
    }


def _review_summary(candidates: list[dict[str, Any]], accepted_cases: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(item["review_status"] for item in candidates)
    category_counts = Counter(case["category"] for case in accepted_cases)
    return {
        "candidate_count": len(candidates),
        "accepted_count": len(accepted_cases),
        "rejected_count": int(status_counts.get("rejected", 0)),
        "status_counts": dict(sorted(status_counts.items())),
        "accepted_category_counts": dict(sorted(category_counts.items())),
        "markdown_annotations_are_authoritative": True,
    }


if __name__ == "__main__":
    raise SystemExit(main())
