#!/usr/bin/env python
"""Generate local M8 agent stress candidates from ignored M3 artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.thinkpad.manifest import load_manifest  # noqa: E402

_DIAGNOSTIC_PROCEDURE_TERMS = (
    "configuration",
    "invalid",
    "failure",
    "uuid",
    "error",
    "diagnostic",
    "system will reboot",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local ThinkPad M8 agent stress candidates.")
    parser.add_argument("--manifest", default="data/manifests/manuals_manifest.yaml")
    parser.add_argument("--extracted-dir", default="data/extracted/m3")
    parser.add_argument("--output", default="data/eval/m8_agent_stress_candidates.json")
    parser.add_argument("--per-manual", type=int, default=24)
    return parser.parse_args()


def main() -> int:
    _configure_windows_stdio()
    args = parse_args()
    extracted = Path(args.extracted_dir)
    manuals = load_manifest(args.manifest)
    by_manual = {manual.manual_id: manual for manual in manuals}
    tables = _read_jsonl(extracted / "tables.jsonl")
    procedures = _read_jsonl(extracted / "fru_procedures.jsonl")
    figures = _read_jsonl(extracted / "figures.jsonl")
    warnings = _read_jsonl(extracted / "warnings.jsonl")

    cases: list[dict[str, Any]] = []
    for manual_id, manual in by_manual.items():
        model = manual.models[0]
        cases.extend(_error_cases(model, manual_id, tables, args.per_manual // 4))
        cases.extend(_screw_cases(model, manual_id, tables, args.per_manual // 4))
        cases.extend(_procedure_cases(model, manual_id, procedures, args.per_manual // 4))
        cases.extend(_supporting_cases(model, manual_id, figures, warnings, args.per_manual - (3 * (args.per_manual // 4))))

    output = {
        "version": "m8_stress_candidates",
        "source": "Generated from local ignored M3 extraction candidates. Use for stress/performance only, not gold accuracy claims.",
        "test_cases": cases,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "case_count": len(cases)}, indent=2))
    return 0


def _configure_windows_stdio() -> None:
    if sys.platform != "win32":
        return
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _error_cases(model: str, manual_id: str, tables: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    rows = [row for row in tables if row.get("manual_id") == manual_id and row.get("table_type") == "error_code"]
    cases = []
    for row in rows[:limit]:
        code = _first_code(json.dumps(row.get("row") or {}))
        if not code:
            continue
        cases.append(_case(f"stress_{manual_id}_error_{code}", "stress_error_code", f"{model} error code {code} repair evidence", "ok", ["resolve_thinkpad_model", "lookup_error_code"], manual_id, ["table"], [code]))
    return cases


def _screw_cases(model: str, manual_id: str, tables: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    rows = [row for row in tables if row.get("manual_id") == manual_id and row.get("table_type") == "screw_spec"]
    cases = []
    for index, row in enumerate(rows[:limit], start=1):
        query = str((row.get("row") or {}).get("Screw (quantity)") or "screw spec")
        cases.append(_case(f"stress_{manual_id}_screw_{index:02d}", "stress_screw_spec", f"{model} screw spec {query}", "ok", ["resolve_thinkpad_model", "get_screw_spec"], manual_id, ["table"], [query.split(",")[0]]))
    return cases


def _procedure_cases(model: str, manual_id: str, procedures: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    rows = [
        row
        for row in procedures
        if row.get("manual_id") == manual_id
        and row.get("fru_id")
        and row.get("fru_name")
        and _is_service_procedure_candidate(row)
    ]
    cases = []
    for row in rows[:limit]:
        component = row.get("fru_name")
        cases.append(_case(f"stress_{manual_id}_procedure_{row.get('fru_id')}", "stress_fru_procedure", f"{model} {component} removal plan", "ok", ["resolve_thinkpad_model", "get_fru_procedure", "get_fru_dependency_chain"], manual_id, ["fru_procedure"], [str(row.get("fru_id"))]))
    return cases


def _supporting_cases(model: str, manual_id: str, figures: list[dict[str, Any]], warnings: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    cases = []
    if limit <= 0:
        return cases
    warning = next((row for row in warnings if row.get("manual_id") == manual_id), None)
    if warning:
        component = warning.get("related_component") or "battery"
        cases.append(_case(f"stress_{manual_id}_warning", "stress_safety", f"{model} {component} safety warning", "ok", ["resolve_thinkpad_model", "get_safety_warnings"], manual_id, ["warning"], [component], safety_required=True))
    if len(cases) >= limit:
        return cases
    figure = next((row for row in figures if row.get("manual_id") == manual_id), None)
    if figure:
        cases.append(_case(f"stress_{manual_id}_diagram", "stress_diagram", f"{model} base cover diagram", "ok", ["resolve_thinkpad_model", "get_related_diagram"], manual_id, ["figure"], []))
    return cases


def _case(
    case_id: str,
    category: str,
    query: str,
    status: str,
    required_tools: list[str],
    manual_id: str,
    record_types: list[str],
    identifiers: list[str],
    safety_required: bool = False,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": category,
        "query": query,
        "expected": {
            "status": status,
            "clarification_needed": status == "clarification_required",
            "required_tools": required_tools,
            "manual_ids": [manual_id],
            "record_types": record_types,
            "identifiers": [item for item in identifiers if item],
            "citation_required": status == "ok",
            "safety_required": safety_required,
            "max_unsupported_claims": 0,
        },
    }


def _first_code(value: str) -> str | None:
    import re

    match = re.search(r"(?<![A-Za-z0-9])([0-9]{4})(?![A-Za-z0-9])", value)
    return match.group(1) if match else None


def _is_service_procedure_candidate(row: dict[str, Any]) -> bool:
    fru_id = str(row.get("fru_id") or "")
    if not fru_id.isdigit():
        return False
    if int(fru_id) % 10 != 0:
        return False
    name = str(row.get("fru_name") or "").lower()
    return not any(term in name for term in _DIAGNOSTIC_PROCEDURE_TERMS)


if __name__ == "__main__":
    raise SystemExit(main())
