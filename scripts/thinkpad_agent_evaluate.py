#!/usr/bin/env python
"""Run the M8 ThinkPad repair-planning agent benchmark."""

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
from src.thinkpad.agent_evaluation import (  # noqa: E402
    evaluate_thinkpad_agent_cases,
    load_thinkpad_agent_golden_set,
)
from src.thinkpad.retrieval import retrieve_thinkpad  # noqa: E402
from src.thinkpad.tool_service import ThinkPadToolService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ThinkPad M8 agent evaluation.")
    parser.add_argument("--golden-set", default="tests/fixtures/thinkpad_m8_agent_golden_set.json")
    parser.add_argument("--manifest", default="data/manifests/manuals_manifest.yaml")
    parser.add_argument("--extracted-dir", default="data/extracted/m3")
    parser.add_argument("--settings", default="config/settings.yaml")
    parser.add_argument("--collection", default="thinkpad_m4")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--mode",
        choices=["deterministic", "live_retrieval", "live_llm"],
        default="deterministic",
    )
    parser.add_argument(
        "--require-live-retrieval",
        action="store_true",
        help="Alias for --mode live_retrieval unless --live-llm is set.",
    )
    parser.add_argument("--live-llm", action="store_true", help="Alias for --mode live_llm.")
    parser.add_argument("--output", default=None, help="Optional JSON report output path.")
    parser.add_argument("--progress-jsonl", default=None, help="Optional per-case progress JSONL path.")
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N cases.")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate at most N cases after offset.")
    parser.add_argument("--llm-repair-attempts", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mode = args.mode
    if args.live_llm:
        mode = "live_llm"
    elif args.require_live_retrieval and mode == "deterministic":
        mode = "live_retrieval"

    try:
        cases = load_thinkpad_agent_golden_set(args.golden_set)
        if args.offset < 0:
            raise ValueError("--offset must be >= 0")
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit must be >= 1")
        cases = cases[args.offset :]
        if args.limit is not None:
            cases = cases[: args.limit]
        settings = load_settings(args.settings)
        retriever = _cached_retriever(settings) if mode in {"live_retrieval", "live_llm"} else None
        service = ThinkPadToolService(
            manifest_path=args.manifest,
            extracted_dir=args.extracted_dir,
            settings=settings,
            retriever=retriever,
        )
        llm = LLMFactory.create(settings) if mode == "live_llm" else None
        report = evaluate_thinkpad_agent_cases(
            cases=cases,
            service=service,
            mode=mode,
            collection=args.collection,
            top_k=args.top_k,
            llm=llm,
            llm_repair_attempts=max(0, args.llm_repair_attempts),
            progress_path=args.progress_jsonl,
        )
    except Exception as exc:
        print(f"ThinkPad agent evaluation failed: {exc}", file=sys.stderr)
        return 1

    report_json = report.to_json()
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_json + "\n", encoding="utf-8")
    print(report_json)
def _cached_retriever(settings):
    from src.thinkpad.retrieval import _create_core_reranker, _create_hybrid_search

    search_by_collection = {}
    reranker = _create_core_reranker(settings)

    def _retrieve(query, manuals, settings, collection="thinkpad_m4", top_k=5):
        search = search_by_collection.get(collection)
        if search is None:
            search = _create_hybrid_search(settings, collection)
            search_by_collection[collection] = search
        return retrieve_thinkpad(
            query=query,
            manuals=manuals,
            settings=settings,
            collection=collection,
            top_k=top_k,
            hybrid_search=search,
            core_reranker=reranker,
        )

    return _retrieve


if __name__ == "__main__":
    raise SystemExit(main())
