#!/usr/bin/env python
"""Run the M6 ThinkPad evaluation baseline."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.core.settings import load_settings  # noqa: E402
from src.thinkpad.evaluation import evaluate_thinkpad_cases, load_thinkpad_golden_set  # noqa: E402
from src.thinkpad.tool_service import ThinkPadToolService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ThinkPad M6 golden evaluation.")
    parser.add_argument("--golden-set", default="tests/fixtures/thinkpad_m6_golden_set.json")
    parser.add_argument("--manifest", default="data/manifests/manuals_manifest.yaml")
    parser.add_argument("--extracted-dir", default="data/extracted/m3")
    parser.add_argument("--settings", default="config/settings.yaml")
    parser.add_argument("--collection", default="thinkpad_m4")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", default=None, help="Optional JSON report output path.")
    parser.add_argument(
        "--require-live-retrieval",
        action="store_true",
        help="Fail if live retrieval cannot run. Requires DASHSCOPE_API_KEY and a local index.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    live_key_available = bool(os.environ.get("DASHSCOPE_API_KEY"))
    run_live_retrieval = bool(args.require_live_retrieval or live_key_available)

    if args.require_live_retrieval and not live_key_available:
        print(
            "live retrieval was required but DASHSCOPE_API_KEY is not set in the local shell",
            file=sys.stderr,
        )
        return 2

    try:
        cases = load_thinkpad_golden_set(args.golden_set)
        settings = load_settings(args.settings)
        service = ThinkPadToolService(
            manifest_path=args.manifest,
            extracted_dir=args.extracted_dir,
            settings=settings,
        )
        report = evaluate_thinkpad_cases(
            cases=cases,
            service=service,
            collection=args.collection,
            top_k=args.top_k,
            run_live_retrieval=run_live_retrieval,
            live_retrieval_required=bool(args.require_live_retrieval),
        )
    except Exception as exc:
        print(f"ThinkPad evaluation failed: {exc}", file=sys.stderr)
        return 1

    report_json = report.to_json()
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_json + "\n", encoding="utf-8")
    print(report_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
