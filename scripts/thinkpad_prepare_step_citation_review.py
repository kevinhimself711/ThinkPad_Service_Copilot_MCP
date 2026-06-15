#!/usr/bin/env python
"""Prepare a local M8.5a step-level citation review pack.

The output is an ignored human annotation aid. It records only short FRU
identifiers, candidate pages, and short step labels so a reviewer can verify
step pages against local Lenovo HMM PDFs without copying manual prose.
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

_TARGET_COUNT = 12
_MIN_CANDIDATES = 8
_STEP_LABEL_LIMIT = 120
_DIAGNOSTIC_PROCEDURE_TERMS = (
    "configuration",
    "invalid",
    "failure",
    "uuid",
    "error",
    "diagnostic",
    "system will reboot",
)


@dataclass(frozen=True)
class StepReviewCandidate:
    """Copyright-light FRU procedure candidate pending step-page review."""

    case_id: str
    category: str
    query: str
    manual_id: str
    fru_id: str
    fru_name: str
    candidate_section_pages: list[int]
    required_tools: list[str]
    pdf_local_path: str | None
    source_record_id: str
    source_record_kind: str
    candidate_steps: list[dict[str, Any]]
    review_status: str = "pending"
    reviewer_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "query": self.query,
            "manual_id": self.manual_id,
            "fru_id": self.fru_id,
            "fru_name": self.fru_name,
            "candidate_section_pages": self.candidate_section_pages,
            "required_tools": self.required_tools,
            "pdf_local_path": self.pdf_local_path,
            "source_record_id": self.source_record_id,
            "source_record_kind": self.source_record_kind,
            "review_status": self.review_status,
            "reviewer_notes": self.reviewer_notes,
            "candidate_steps": self.candidate_steps,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare M8.5a step-level citation review pack.")
    parser.add_argument("--manifest", default="data/manifests/manuals_manifest.yaml")
    parser.add_argument("--extracted-dir", default="data/extracted/m3")
    parser.add_argument("--output", default="data/eval/m8_5_step_citation_review.json")
    parser.add_argument("--markdown-output", default="data/eval/m8_5_step_citation_review.md")
    parser.add_argument("--target-count", type=int, default=_TARGET_COUNT)
    return parser.parse_args()


def main() -> int:
    _configure_windows_stdio()
    args = parse_args()
    pack = build_step_review_pack(
        manifest=args.manifest,
        extracted_dir=args.extracted_dir,
        target_count=args.target_count,
    )
    output_path = Path(args.output)
    markdown_path = Path(args.markdown_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_step_review_markdown(pack), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "markdown_output": str(markdown_path),
                "candidate_count": pack["candidate_count"],
                "multi_page_candidate_count": pack["multi_page_candidate_count"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _configure_windows_stdio() -> None:
    if sys.platform != "win32":
        return
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def build_step_review_pack(
    manifest: str | Path,
    extracted_dir: str | Path,
    target_count: int = _TARGET_COUNT,
) -> dict[str, Any]:
    """Build a local step-level citation review pack from M3 extraction artifacts."""

    manuals = load_manifest(manifest)
    extracted = Path(extracted_dir)
    _require_step_inputs(extracted)
    procedures = _read_jsonl(extracted / "fru_procedures.jsonl")
    if procedures and not any(isinstance(row.get("step_records"), list) for row in procedures):
        raise ValueError(
            "fru_procedures.jsonl has no step_records; rerun scripts/thinkpad_extract_hmm.py "
            "after M8.5a step provenance changes"
        )

    manual_by_id = {manual.manual_id: manual for manual in manuals}
    candidates = _select_step_candidates(manuals, procedures, target_count=target_count)
    candidate_dicts = [candidate.to_dict() for candidate in candidates]
    multi_page_count = sum(1 for item in candidate_dicts if _candidate_has_multiple_step_pages(item))
    return {
        "version": "m8_5a_step_citation_review_pack",
        "source": (
            "Local human review pack generated from ignored M3 extraction artifacts. "
            "This is not a human gold set until every candidate step is verified against the PDF."
        ),
        "review_instructions": [
            "Open pdf_local_path for each candidate.",
            "For each candidate step, compare candidate_page with the PDF page containing that step.",
            "Set the case review_status to verified, corrected, or rejected.",
            "For each step, set review_status to verified, corrected, or not_applicable.",
            "When corrected, set verified_page to the true PDF page number.",
            "Do not copy Lenovo manual prose into reviewer_notes.",
        ],
        "target_count": target_count,
        "minimum_target_count": _MIN_CANDIDATES,
        "candidate_count": len(candidate_dicts),
        "manual_count": len(manual_by_id),
        "multi_page_candidate_count": multi_page_count,
        "candidates": candidate_dicts,
    }


def render_step_review_markdown(pack: dict[str, Any]) -> str:
    """Render a Markdown review aid that the human reviewer edits locally."""

    lines = [
        "# M8.5a Step-Level Citation Review Pack",
        "",
        "This is a local review aid, not a committed human gold set.",
        "",
        "For each candidate, open the listed PDF and verify each step page. Do not copy Lenovo manual prose.",
        "",
        "Case status values: `verified`, `corrected`, `rejected`.",
        "Step status values: `verified`, `corrected`, `not_applicable`.",
        "",
    ]
    for index, item in enumerate(pack.get("candidates", []), start=1):
        lines.extend(
            [
                f"## {index}. {item['case_id']}",
                "",
                f"- Category: `{item['category']}`",
                f"- Query: `{item['query']}`",
                f"- Manual: `{item['manual_id']}`",
                f"- FRU: `{item['fru_id']} {item['fru_name']}`",
                f"- Candidate section pages: `{item.get('candidate_section_pages') or []}`",
                f"- Required tools: `{item.get('required_tools') or []}`",
                f"- PDF: `{item.get('pdf_local_path') or ''}`",
                f"- Source record: `{item.get('source_record_kind') or ''}:{item.get('source_record_id') or ''}`",
                "- Review status: `pending`",
                "- Reviewer notes: ``",
                "",
                "### Steps",
                "",
            ]
        )
        for step in item.get("candidate_steps") or []:
            lines.extend(
                [
                    f"#### Step {step['step_index']}",
                    "",
                    f"- Step label: `{step['step_label']}`",
                    f"- Candidate page: `{step.get('candidate_page') or ''}`",
                    "- Review status: `pending`",
                    "- Verified page: ``",
                    "- Reviewer notes: ``",
                    "",
                ]
            )
    return "\n".join(lines) + "\n"


def _require_step_inputs(extracted: Path) -> None:
    if not extracted.exists():
        raise FileNotFoundError(f"extracted-dir does not exist: {extracted}")
    required = extracted / "fru_procedures.jsonl"
    if not required.exists():
        raise FileNotFoundError(f"extracted-dir is missing required file: {required.name}")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _select_step_candidates(
    manuals: list[ManualMetadata],
    procedures: list[dict[str, Any]],
    target_count: int,
) -> list[StepReviewCandidate]:
    manual_by_id = {manual.manual_id: manual for manual in manuals}
    rows = [
        row for row in procedures
        if row.get("manual_id") in manual_by_id
        and _is_service_procedure(row)
        and _candidate_steps(row)
    ]
    rows.sort(
        key=lambda row: (
            -len(_unique_step_pages(row)),
            -len(_candidate_steps(row)),
            str(row.get("manual_id") or ""),
            str(row.get("fru_id") or ""),
        )
    )

    selected: list[StepReviewCandidate] = []
    used_manuals: set[str] = set()
    for row in rows:
        manual_id = str(row.get("manual_id") or "")
        if manual_id in used_manuals and len(selected) < min(target_count, len(manuals)):
            continue
        selected.append(_to_candidate(manual_by_id[manual_id], row))
        used_manuals.add(manual_id)
        if len(selected) >= target_count:
            return selected

    for row in rows:
        if len(selected) >= target_count:
            return selected
        case_id = _case_id(row)
        if any(candidate.case_id == case_id for candidate in selected):
            continue
        selected.append(_to_candidate(manual_by_id[str(row.get("manual_id"))], row))
    return selected


def _to_candidate(manual: ManualMetadata, row: dict[str, Any]) -> StepReviewCandidate:
    fru_id = str(row.get("fru_id") or "")
    fru_name = _short_label(row.get("fru_name") or "FRU")
    category = (
        "fru_procedure_step_pages"
        if len(_unique_step_pages(row)) >= 2
        else "fru_procedure_single_page_control"
    )
    return StepReviewCandidate(
        case_id=_case_id(row),
        category=category,
        query=f"{manual.models[0]} {fru_name} removal plan",
        manual_id=manual.manual_id,
        fru_id=fru_id,
        fru_name=fru_name,
        candidate_section_pages=_section_pages(row),
        required_tools=["resolve_thinkpad_model", "get_fru_procedure"],
        pdf_local_path=manual.local_pdf_path,
        source_record_id=str(row.get("procedure_id") or ""),
        source_record_kind="fru_procedure",
        candidate_steps=_candidate_steps(row),
    )


def _candidate_steps(row: dict[str, Any]) -> list[dict[str, Any]]:
    raw_steps = row.get("step_records")
    if not isinstance(raw_steps, list):
        return []
    steps: list[dict[str, Any]] = []
    for raw in raw_steps:
        if not isinstance(raw, dict):
            continue
        text = _short_label(raw.get("text") or "", _STEP_LABEL_LIMIT)
        if not text or _is_review_noise(text):
            continue
        if not _is_action_like_step_text(text):
            continue
        citation = raw.get("citation") if isinstance(raw.get("citation"), dict) else {}
        page = _to_int(citation.get("page_start"))
        if page is None:
            continue
        steps.append(
            {
                "step_index": _to_int(raw.get("step_index")) or len(steps) + 1,
                "step_label": text,
                "candidate_page": page,
                "citation_source": raw.get("citation_source") or "unknown",
                "review_status": "pending",
                "verified_page": None,
                "reviewer_notes": "",
            }
        )
    return steps[:8]


def _is_service_procedure(row: dict[str, Any]) -> bool:
    fru_id = str(row.get("fru_id") or "")
    if not fru_id.isdigit() or int(fru_id) % 10 != 0:
        return False
    name = str(row.get("fru_name") or "").lower()
    return not any(term in name for term in _DIAGNOSTIC_PROCEDURE_TERMS)


def _unique_step_pages(row: dict[str, Any]) -> set[int]:
    return {
        int(step["candidate_page"])
        for step in _candidate_steps(row)
        if _to_int(step.get("candidate_page")) is not None
    }


def _section_pages(row: dict[str, Any]) -> list[int]:
    citation = row.get("citation") if isinstance(row.get("citation"), dict) else {}
    start = _to_int(citation.get("page_start") or row.get("page_start"))
    end = _to_int(citation.get("page_end") or row.get("page_end") or start)
    if start is None:
        return []
    if end is None or end <= start:
        return [start]
    return list(range(start, end + 1))


def _case_id(row: dict[str, Any]) -> str:
    return f"m8_5a_{row.get('manual_id')}_fru_{row.get('fru_id')}"


def _short_label(value: Any, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _is_review_noise(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return True
    if normalized in {"step", "screw (quantity)", "color", "torque"}:
        return True
    if re.fullmatch(r"[0-9]+", normalized):
        return True
    if normalized.startswith("[[page "):
        return True
    if "hardware maintenance manual" in normalized:
        return True
    if normalized in {"when installing:", "when installing", "for access, remove these frus:"}:
        return True
    if normalized.startswith("for access, remove"):
        return True
    if normalized.startswith(("installation steps of", "removal steps of")):
        return True
    return False


def _is_action_like_step_text(text: str) -> bool:
    normalized = text.lower()
    action_terms = (
        "remove",
        "disconnect",
        "detach",
        "lift",
        "loosen",
        "install",
        "attach",
        "connect",
        "ensure",
        "route",
        "turn off",
        "unplug",
        "disable",
        "slide",
        "pull",
        "open",
    )
    return any(term in normalized for term in action_terms)


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _candidate_has_multiple_step_pages(item: dict[str, Any]) -> bool:
    pages = {
        int(step["candidate_page"])
        for step in item.get("candidate_steps") or []
        if _to_int(step.get("candidate_page")) is not None
    }
    return len(pages) >= 2


if __name__ == "__main__":
    raise SystemExit(main())
