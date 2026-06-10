#!/usr/bin/env python
"""Build local ThinkPad retrieval indexes from M3 extraction artifacts."""

from __future__ import annotations

import argparse
import json
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
from src.thinkpad.manifest import load_manifest  # noqa: E402
from src.thinkpad.retrieval_index import build_thinkpad_retrieval_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ThinkPad M4 local retrieval index.")
    parser.add_argument("--manifest", default="data/manifests/manuals_manifest.yaml")
    parser.add_argument("--settings", default="config/settings.yaml")
    parser.add_argument("--extracted-dir", default="data/extracted/m3")
    parser.add_argument("--collection", default="thinkpad_m4")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Embedding batch size. DashScope text-embedding-v4 live indexing uses at most 10.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-clear", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manuals = load_manifest(args.manifest)
    settings = None if args.dry_run else load_settings(args.settings)
    result = build_thinkpad_retrieval_index(
        extracted_dir=args.extracted_dir,
        manuals=manuals,
        settings=settings,
        collection=args.collection,
        limit=args.limit,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        force_clear=args.force_clear,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
