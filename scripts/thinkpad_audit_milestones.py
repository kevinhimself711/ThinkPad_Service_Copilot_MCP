#!/usr/bin/env python
"""Collect local M0-M7 audit facts for ThinkPad milestone reporting."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


TRACKED_EVIDENCE_FILES = [
    "AGENTS.md",
    "docs/M0_BASELINE.md",
    "docs/SPIKE_REPORT.md",
    "docs/PROJECT_GUIDE.md",
    "docs/DEV_SPEC_THINKPAD.md",
    "docs/EXPERIMENTS.md",
    "docs/EVAL_REPORT.md",
    "docs/IMPLEMENTATION_LOG.md",
    "config/manuals_manifest.example.yaml",
    "src/thinkpad/models.py",
    "src/thinkpad/manifest.py",
    "src/thinkpad/model_resolver.py",
    "src/thinkpad/hmm_loader.py",
    "src/thinkpad/table_extractor.py",
    "src/thinkpad/figure_extractor.py",
    "src/thinkpad/fru_extractor.py",
    "src/thinkpad/safety.py",
    "src/thinkpad/retrieval.py",
    "src/thinkpad/tool_service.py",
    "src/thinkpad/fru_graph.py",
    "src/mcp_server/tools/thinkpad_tools.py",
    "tests/fixtures/thinkpad_m6_golden_set.json",
    "tests/fixtures/thinkpad_m7_golden_set.json",
]

LOCAL_ARTIFACTS = [
    "data/manifests/manuals_manifest.yaml",
    "data/extracted/m3/summary.json",
    "data/eval/m6_report_structured.json",
    "data/eval/m6_report.json",
    "data/eval/m7_report_structured.json",
    "data/eval/m7_report_live.json",
    "data/db/bm25",
    "data/db/chroma",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect ThinkPad M0-M7 audit facts.")
    parser.add_argument("--output", default="data/eval/m0_m7_audit.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = {
        "version": "m7.1",
        "git": _git_facts(),
        "tracked_evidence": _path_facts(TRACKED_EVIDENCE_FILES),
        "local_artifacts": _path_facts(LOCAL_ARTIFACTS),
        "m3_extraction": _json_file("data/extracted/m3/summary.json"),
        "m6_structured_eval": _eval_summary("data/eval/m6_report_structured.json"),
        "m6_live_eval": _eval_summary("data/eval/m6_report.json"),
        "m7_structured_eval": _eval_summary("data/eval/m7_report_structured.json"),
        "m7_live_eval": _eval_summary("data/eval/m7_report_live.json"),
        "golden_sets": {
            "m6": _golden_count("tests/fixtures/thinkpad_m6_golden_set.json"),
            "m7": _golden_count("tests/fixtures/thinkpad_m7_golden_set.json"),
        },
    }
    output = REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def _git_facts() -> dict[str, Any]:
    return {
        "branch": _git(["branch", "--show-current"]),
        "head": _git(["rev-parse", "--short", "HEAD"]),
        "head_subject": _git(["log", "-1", "--pretty=%s"]),
        "upstream_status": _git(["status", "-sb", "--untracked-files=no"]),
        "recent_commits": [
            _parse_commit_line(line)
            for line in _git(["log", "--oneline", "--decorate", "-10"]).splitlines()
            if line.strip()
        ],
    }


def _path_facts(paths: list[str]) -> dict[str, dict[str, Any]]:
    facts: dict[str, dict[str, Any]] = {}
    for path in paths:
        absolute = REPO_ROOT / path
        facts[path] = {
            "exists": absolute.exists(),
            "is_dir": absolute.is_dir(),
            "size_bytes": _path_size(absolute) if absolute.exists() and absolute.is_file() else None,
        }
    return facts


def _json_file(path: str) -> dict[str, Any]:
    absolute = REPO_ROOT / path
    if not absolute.exists():
        return {"exists": False}
    with absolute.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {"exists": True, "data": data}


def _eval_summary(path: str) -> dict[str, Any]:
    loaded = _json_file(path)
    if not loaded.get("exists"):
        return loaded
    data = loaded["data"]
    return {
        "exists": True,
        "version": data.get("version"),
        "query_count": data.get("query_count"),
        "environment": data.get("environment", {}),
        "aggregate_metrics": data.get("aggregate_metrics", {}),
    }


def _golden_count(path: str) -> dict[str, Any]:
    loaded = _json_file(path)
    if not loaded.get("exists"):
        return loaded
    cases = loaded["data"].get("test_cases", [])
    return {"exists": True, "case_count": len(cases)}


def _path_size(path: Path) -> int:
    return path.stat().st_size


def _git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


def _parse_commit_line(line: str) -> dict[str, str]:
    commit, _, subject = line.partition(" ")
    return {"commit": commit.strip(), "subject": subject.strip()}


if __name__ == "__main__":
    raise SystemExit(main())
