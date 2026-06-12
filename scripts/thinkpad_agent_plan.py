#!/usr/bin/env python
"""Run one ThinkPad repair-planning agent query."""

from __future__ import annotations

import argparse
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
from src.libs.llm.llm_factory import LLMFactory  # noqa: E402
from src.thinkpad.agent import plan_thinkpad_repair  # noqa: E402
from src.thinkpad.tool_service import ThinkPadToolService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one ThinkPad repair-planning agent query.")
    parser.add_argument("query", help="Free-form repair-planning query.")
    parser.add_argument("--manifest", default="data/manifests/manuals_manifest.yaml")
    parser.add_argument("--extracted-dir", default="data/extracted/m3")
    parser.add_argument("--settings", default="config/settings.yaml")
    parser.add_argument("--collection", default="thinkpad_m4")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", default=None, help="Optional JSON output path.")
    parser.add_argument("--no-llm", action="store_true", help="Force deterministic evidence-only output.")
    parser.add_argument("--live-llm", action="store_true", help="Use configured live LLM for cited prose composition.")
    parser.add_argument("--use-retrieval", action="store_true", help="Include retrieval evidence in the plan.")
    parser.add_argument(
        "--require-live-retrieval",
        action="store_true",
        help="Treat retrieval failure as an agent error.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        settings = load_settings(args.settings)
        service = ThinkPadToolService(
            manifest_path=args.manifest,
            extracted_dir=args.extracted_dir,
            settings=settings,
        )
        llm = None
        if args.live_llm:
            llm = LLMFactory.create(settings)
        result = plan_thinkpad_repair(
            query=args.query,
            service=service,
            use_llm=bool(args.live_llm and not args.no_llm),
            llm=llm,
            collection=args.collection,
            top_k=args.top_k,
            use_retrieval=bool(args.use_retrieval or args.require_live_retrieval),
            require_live_retrieval=bool(args.require_live_retrieval),
        )
    except Exception as exc:
        print(f"ThinkPad agent planning failed: {exc}", file=sys.stderr)
        return 1

    output = result.to_json()
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
