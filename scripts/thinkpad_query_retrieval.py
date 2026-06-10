#!/usr/bin/env python
"""Run a ThinkPad M4 retrieval query and print JSON results."""

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
from src.thinkpad.manifest import load_manifest  # noqa: E402
from src.thinkpad.retrieval import retrieve_thinkpad  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the local ThinkPad M4 retrieval index.")
    parser.add_argument("query")
    parser.add_argument("--manifest", default="data/manifests/manuals_manifest.yaml")
    parser.add_argument("--settings", default="config/settings.yaml")
    parser.add_argument("--collection", default="thinkpad_m4")
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manuals = load_manifest(args.manifest)
    settings = load_settings(args.settings)
    response = retrieve_thinkpad(
        query=args.query,
        manuals=manuals,
        settings=settings,
        collection=args.collection,
        top_k=args.top_k,
    )
    print(response.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
