#!/usr/bin/env python
"""Prepare a local human-review pack for M8.4 human gold evaluation.

The output is intentionally a review artifact, not a committed golden set.
It contains only copyright-light identifiers, pages, record IDs, and local PDF
paths so a human reviewer can verify pages against local Lenovo HMM PDFs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.thinkpad.manifest import ManualMetadata, load_manifest  # noqa: E402

_DIAGNOSTIC_PROCEDURE_TERMS = (
    "configuration",
    "invalid",
    "failure",
    "uuid",
    "error",
    "diagnostic",
    "system will reboot",
)

_TARGET_COUNTS = {
    "fru_procedure": 6,
    "fru_dependency_chain": 3,
    "table": 4,
    "supporting_evidence": 3,
    "negative": 2,
}


@dataclass(frozen=True)
class ReviewCandidate:
    """Copyright-light candidate record pending human page verification."""

    case_id: str
    category: str
    query: str
    expected_status: str
    manual_id: str | None
    candidate_pages: list[int]
    record_type: str | None
    identifier: str | None
    required_tools: list[str]
    pdf_local_path: str | None
    source_record_id: str | None
    source_record_kind: str | None
    review_status: str = "pending"
    verified_pages: list[int] | None = None
    reviewer_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "query": self.query,
            "expected_status": self.expected_status,
            "manual_id": self.manual_id,
            "candidate_pages": self.candidate_pages,
            "record_type": self.record_type,
            "identifier": self.identifier,
            "required_tools": self.required_tools,
            "pdf_local_path": self.pdf_local_path,
            "source_record_id": self.source_record_id,
            "source_record_kind": self.source_record_kind,
            "review_status": self.review_status,
            "verified_pages": self.verified_pages or [],
            "reviewer_notes": self.reviewer_notes,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a local M8.4 human gold review pack.")
    parser.add_argument("--manifest", default="data/manifests/manuals_manifest.yaml")
    parser.add_argument("--extracted-dir", default="data/extracted/m3")
    parser.add_argument("--output", default="data/eval/m8_4_human_gold_review.json")
    parser.add_argument("--markdown-output", default="data/eval/m8_4_human_gold_review.md")
    return parser.parse_args()


def main() -> int:
    _configure_windows_stdio()
    args = parse_args()
    pack = build_review_pack(args.manifest, args.extracted_dir)
    output_path = Path(args.output)
    markdown_path = Path(args.markdown_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_review_markdown(pack), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "markdown_output": str(markdown_path), "candidate_count": len(pack["candidates"])}, indent=2))
    return 0


def _configure_windows_stdio() -> None:
    if sys.platform != "win32":
        return
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def build_review_pack(manifest: str | Path, extracted_dir: str | Path) -> dict[str, Any]:
    manuals = load_manifest(manifest)
    extracted = Path(extracted_dir)
    _require_extracted_inputs(extracted)
    records = {
        "procedures": _read_jsonl(extracted / "fru_procedures.jsonl"),
        "tables": _read_jsonl(extracted / "tables.jsonl"),
        "warnings": _read_jsonl(extracted / "warnings.jsonl"),
        "figures": _read_jsonl(extracted / "figures.jsonl"),
        "dependency_edges": _read_jsonl(extracted / "dependency_edges.jsonl"),
    }
    by_manual = {manual.manual_id: manual for manual in manuals}
    procedure_by_key = {
        (str(row.get("manual_id")), str(row.get("fru_id"))): row
        for row in records["procedures"]
        if row.get("manual_id") and row.get("fru_id")
    }

    candidates: list[ReviewCandidate] = []
    used_case_ids: set[str] = set()
    used_manual_categories: set[tuple[str | None, str]] = set()

    _extend_unique(
        candidates,
        used_case_ids,
        used_manual_categories,
        _procedure_candidates(manuals, records["procedures"]),
        _TARGET_COUNTS["fru_procedure"],
    )
    _extend_unique(
        candidates,
        used_case_ids,
        used_manual_categories,
        _dependency_candidates(manuals, records["dependency_edges"], procedure_by_key),
        _TARGET_COUNTS["fru_dependency_chain"],
    )
    _extend_unique(
        candidates,
        used_case_ids,
        used_manual_categories,
        _table_candidates(manuals, records["tables"]),
        _TARGET_COUNTS["table"],
    )
    _extend_unique(
        candidates,
        used_case_ids,
        used_manual_categories,
        _supporting_candidates(manuals, records["warnings"], records["figures"]),
        _TARGET_COUNTS["supporting_evidence"],
    )
    _extend_unique(
        candidates,
        used_case_ids,
        used_manual_categories,
        _negative_candidates(),
        _TARGET_COUNTS["negative"],
    )

    candidate_dicts = [candidate.to_dict() for candidate in candidates]
    return {
        "version": "m8_4a_review_pack",
        "source": "Candidate review pack generated from local ignored M3 extraction artifacts. Human verification is required before any case becomes gold. No Lenovo manual prose is copied.",
        "review_instructions": [
            "Open pdf_local_path and verify candidate_pages against the local HMM PDF.",
            "Set review_status to verified, corrected, or rejected.",
            "When corrected, put the true page numbers in verified_pages.",
            "Do not copy Lenovo manual prose into reviewer_notes.",
        ],
        "target_counts": dict(_TARGET_COUNTS),
        "candidate_count": len(candidate_dicts),
        "manual_count": len(by_manual),
        "candidates": candidate_dicts,
    }


def render_review_markdown(pack: dict[str, Any]) -> str:
    lines = [
        "# M8.4a Human Gold Review Pack",
        "",
        "This is a local review aid, not a committed human gold set.",
        "",
        "For each candidate, open the listed PDF and verify the candidate page. Do not copy Lenovo manual prose into this file.",
        "",
        "Allowed review statuses: `verified`, `corrected`, `rejected`.",
        "",
    ]
    for index, item in enumerate(pack.get("candidates", []), start=1):
        lines.extend(
            [
                f"## {index}. {item['case_id']}",
                "",
                f"- Category: `{item['category']}`",
                f"- Query: `{item['query']}`",
                f"- Manual: `{item.get('manual_id') or ''}`",
                f"- Candidate pages: `{item.get('candidate_pages') or []}`",
                f"- Record type: `{item.get('record_type') or ''}`",
                f"- Identifier: `{item.get('identifier') or ''}`",
                f"- Required tools: `{item.get('required_tools') or []}`",
                f"- PDF: `{item.get('pdf_local_path') or ''}`",
                f"- Source record: `{item.get('source_record_kind') or ''}:{item.get('source_record_id') or ''}`",
                "- Review status: `pending`",
                "- Verified pages: `[]`",
                "- Reviewer notes: ``",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _require_extracted_inputs(extracted: Path) -> None:
    if not extracted.exists():
        raise FileNotFoundError(f"extracted-dir does not exist: {extracted}")
    required = [
        "fru_procedures.jsonl",
        "tables.jsonl",
        "warnings.jsonl",
        "figures.jsonl",
        "dependency_edges.jsonl",
    ]
    missing = [name for name in required if not (extracted / name).exists()]
    if missing:
        raise FileNotFoundError(f"extracted-dir is missing required files: {', '.join(missing)}")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _extend_unique(
    selected: list[ReviewCandidate],
    used_case_ids: set[str],
    used_manual_categories: set[tuple[str | None, str]],
    candidates: list[ReviewCandidate],
    limit: int,
) -> None:
    added = 0
    for candidate in candidates:
        if added >= limit:
            return
        if candidate.case_id in used_case_ids:
            continue
        key = (candidate.manual_id, candidate.category)
        if key in used_manual_categories and candidate.category != "negative":
            continue
        used_case_ids.add(candidate.case_id)
        used_manual_categories.add(key)
        selected.append(candidate)
        added += 1


def _procedure_candidates(manuals: list[ManualMetadata], procedures: list[dict[str, Any]]) -> list[ReviewCandidate]:
    rows_by_manual = _group_by_manual(procedures)
    candidates: list[ReviewCandidate] = []
    for manual in manuals:
        row = _best_procedure(rows_by_manual.get(manual.manual_id, []))
        if not row:
            continue
        fru_id = str(row.get("fru_id") or "")
        fru_name = _short_identifier(row.get("fru_name") or "FRU")
        candidates.append(
            ReviewCandidate(
                case_id=f"m8_4a_{manual.manual_id}_fru_{fru_id}",
                category="fru_procedure",
                query=f"{manual.models[0]} {fru_name} removal plan",
                expected_status="ok",
                manual_id=manual.manual_id,
                candidate_pages=_pages_from_record(row),
                record_type="fru_procedure",
                identifier=fru_id,
                required_tools=["resolve_thinkpad_model", "get_fru_procedure"],
                pdf_local_path=manual.local_pdf_path,
                source_record_id=str(row.get("procedure_id") or ""),
                source_record_kind="fru_procedure",
            )
        )
    return candidates


def _dependency_candidates(
    manuals: list[ManualMetadata],
    edges: list[dict[str, Any]],
    procedure_by_key: dict[tuple[str, str], dict[str, Any]],
) -> list[ReviewCandidate]:
    rows_by_manual = _group_by_manual(edges)
    candidates: list[ReviewCandidate] = []
    for manual in reversed(manuals):
        rows = [row for row in rows_by_manual.get(manual.manual_id, []) if row.get("source_fru_id")]
        if not rows:
            continue
        row = sorted(rows, key=lambda item: (str(item.get("source_fru_id")), str(item.get("required_fru_id"))))[0]
        source_fru_id = str(row.get("source_fru_id") or "")
        procedure = procedure_by_key.get((manual.manual_id, source_fru_id), {})
        component = _short_identifier(procedure.get("fru_name") or f"FRU {source_fru_id}")
        candidates.append(
            ReviewCandidate(
                case_id=f"m8_4a_{manual.manual_id}_chain_{source_fru_id}",
                category="fru_dependency_chain",
                query=f"{manual.models[0]} {component} prerequisite chain",
                expected_status="ok",
                manual_id=manual.manual_id,
                candidate_pages=_pages_from_record(row),
                record_type="fru_dependency_chain",
                identifier=source_fru_id,
                required_tools=["resolve_thinkpad_model", "get_fru_dependency_chain"],
                pdf_local_path=manual.local_pdf_path,
                source_record_id=f"{source_fru_id}->{row.get('required_fru_id')}",
                source_record_kind="dependency_edge",
            )
        )
    return candidates


def _table_candidates(manuals: list[ManualMetadata], tables: list[dict[str, Any]]) -> list[ReviewCandidate]:
    rows_by_manual = _group_by_manual(tables)
    candidates: list[ReviewCandidate] = []
    for manual in manuals:
        error = _first_table(rows_by_manual.get(manual.manual_id, []), "error_code")
        if error:
            code = _first_code(json.dumps(error.get("row") or {}, ensure_ascii=False)) or "error code"
            candidates.append(
                ReviewCandidate(
                    case_id=f"m8_4a_{manual.manual_id}_error_{code}",
                    category="table",
                    query=f"{manual.models[0]} error code {code} repair evidence",
                    expected_status="ok",
                    manual_id=manual.manual_id,
                    candidate_pages=_pages_from_record(error),
                    record_type="table",
                    identifier=code,
                    required_tools=["resolve_thinkpad_model", "lookup_error_code"],
                    pdf_local_path=manual.local_pdf_path,
                    source_record_id=str(error.get("record_id") or ""),
                    source_record_kind="table:error_code",
                )
            )
        screw = _first_table(rows_by_manual.get(manual.manual_id, []), "screw_spec")
        if screw:
            identifier = _screw_identifier(screw.get("row") or {})
            candidates.append(
                ReviewCandidate(
                    case_id=f"m8_4a_{manual.manual_id}_screw_{_slug(identifier)}",
                    category="table",
                    query=f"{manual.models[0]} screw spec {identifier}",
                    expected_status="ok",
                    manual_id=manual.manual_id,
                    candidate_pages=_pages_from_record(screw),
                    record_type="table",
                    identifier=identifier,
                    required_tools=["resolve_thinkpad_model", "get_screw_spec"],
                    pdf_local_path=manual.local_pdf_path,
                    source_record_id=str(screw.get("record_id") or ""),
                    source_record_kind="table:screw_spec",
                )
            )
    return candidates


def _supporting_candidates(
    manuals: list[ManualMetadata],
    warnings: list[dict[str, Any]],
    figures: list[dict[str, Any]],
) -> list[ReviewCandidate]:
    warnings_by_manual = _group_by_manual(warnings)
    figures_by_manual = _group_by_manual(figures)
    candidates: list[ReviewCandidate] = []
    for manual in manuals:
        warning = next((row for row in warnings_by_manual.get(manual.manual_id, []) if row.get("related_component")), None)
        if warning:
            component = _short_identifier(warning.get("related_component") or "safety")
            warning_id = str(warning.get("warning_id") or "")
            candidates.append(
                ReviewCandidate(
                    case_id=f"m8_4a_{manual.manual_id}_warning_{_slug(component)}",
                    category="supporting_evidence",
                    query=f"{manual.models[0]} {component} safety warning",
                    expected_status="ok",
                    manual_id=manual.manual_id,
                    candidate_pages=_pages_from_record(warning),
                    record_type="warning",
                    identifier=component,
                    required_tools=["resolve_thinkpad_model", "get_safety_warnings"],
                    pdf_local_path=manual.local_pdf_path,
                    source_record_id=warning_id,
                    source_record_kind="warning",
                )
            )
        figure = next((row for row in figures_by_manual.get(manual.manual_id, []) if int(row.get("page") or 0) > 20), None)
        if figure:
            image_id = str(figure.get("image_id") or "")
            candidates.append(
                ReviewCandidate(
                    case_id=f"m8_4a_{manual.manual_id}_figure",
                    category="supporting_evidence",
                    query=f"{manual.models[0]} related service diagram",
                    expected_status="ok",
                    manual_id=manual.manual_id,
                    candidate_pages=_pages_from_record(figure),
                    record_type="figure",
                    identifier=image_id,
                    required_tools=["resolve_thinkpad_model", "get_related_diagram"],
                    pdf_local_path=manual.local_pdf_path,
                    source_record_id=image_id,
                    source_record_kind="figure",
                )
            )
    return candidates


def _negative_candidates() -> list[ReviewCandidate]:
    return [
        ReviewCandidate(
            case_id="m8_4a_negative_ambiguous_x1_carbon_battery",
            category="negative",
            query="X1 Carbon battery removal plan",
            expected_status="clarification_required",
            manual_id=None,
            candidate_pages=[],
            record_type=None,
            identifier="generation_required",
            required_tools=["resolve_thinkpad_model"],
            pdf_local_path=None,
            source_record_id=None,
            source_record_kind="negative:model_ambiguity",
        ),
        ReviewCandidate(
            case_id="m8_4a_negative_unsupported_t14_gen5_battery",
            category="negative",
            query="ThinkPad T14 Gen 5 battery removal plan",
            expected_status="not_found",
            manual_id=None,
            candidate_pages=[],
            record_type=None,
            identifier="unsupported_model",
            required_tools=["resolve_thinkpad_model"],
            pdf_local_path=None,
            source_record_id=None,
            source_record_kind="negative:unsupported_generation",
        ),
    ]


def _group_by_manual(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        manual_id = str(row.get("manual_id") or "")
        if manual_id:
            grouped.setdefault(manual_id, []).append(row)
    return grouped


def _best_procedure(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    service_rows = [row for row in rows if _is_service_procedure(row)]
    if not service_rows:
        return None
    preferred_terms = ("battery", "base cover", "memory", "solid-state", "ssd", "fan", "system board")
    for term in preferred_terms:
        match = next((row for row in service_rows if term in str(row.get("fru_name") or "").lower()), None)
        if match:
            return match
    return sorted(service_rows, key=lambda item: str(item.get("fru_id") or ""))[0]


def _is_service_procedure(row: dict[str, Any]) -> bool:
    fru_id = str(row.get("fru_id") or "")
    if not fru_id.isdigit() or int(fru_id) % 10 != 0:
        return False
    name = str(row.get("fru_name") or "").lower()
    return not any(term in name for term in _DIAGNOSTIC_PROCEDURE_TERMS)


def _first_table(rows: list[dict[str, Any]], table_type: str) -> dict[str, Any] | None:
    return next((row for row in rows if row.get("table_type") == table_type), None)


def _pages_from_record(row: dict[str, Any]) -> list[int]:
    page = _to_int(row.get("page"))
    if page is not None:
        return [page]
    citation = row.get("citation") if isinstance(row.get("citation"), dict) else {}
    start = _to_int(citation.get("page_start") or row.get("page_start"))
    end = _to_int(citation.get("page_end") or row.get("page_end") or start)
    if start is None:
        return []
    if end is None or end == start:
        return [start]
    return list(range(start, end + 1))


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_code(value: str) -> str | None:
    match = re.search(r"(?<![A-Za-z0-9])([0-9]{4})(?![A-Za-z0-9])", value)
    return match.group(1) if match else None


def _screw_identifier(row: dict[str, Any]) -> str:
    for key in ("Screw (quantity)", "Screw", "Type", "Size", "Torque"):
        value = str(row.get(key) or "").strip()
        if value:
            return _short_identifier(value)
    return "screw spec"


def _short_identifier(value: Any, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return slug[:50] or "item"


if __name__ == "__main__":
    raise SystemExit(main())
