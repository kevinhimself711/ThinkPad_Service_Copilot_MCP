#!/usr/bin/env python
"""Run local PDF structure inspection for the ThinkPad M1 spike."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.thinkpad.manifest import load_manifest
from src.thinkpad.spike import summarize_pdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect local HMM PDFs for M1 spike risks.")
    parser.add_argument("--manifest", help="Manifest YAML with local_pdf_path entries.")
    parser.add_argument("--pdf", action="append", default=[], help="Additional PDF path to inspect.")
    parser.add_argument(
        "--output",
        default="data/extracted/m1_spike_summary.json",
        help="JSON output path under ignored data/extracted.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit pages per PDF for quick smoke runs. Default scans the full PDF.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reports = []
    failures = []

    if args.manifest:
        for manual in load_manifest(args.manifest):
            try:
                reports.append(
                    summarize_pdf(
                        manual.local_pdf_path,
                        manual_id=manual.manual_id,
                        max_pages=args.max_pages,
                    )
                )
                print(f"[OK] inspected {manual.manual_id}")
            except Exception as exc:
                failures.append(
                    {
                        "manual_id": manual.manual_id,
                        "pdf_path": manual.local_pdf_path,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                print(f"[FAIL] {manual.manual_id}: {type(exc).__name__}: {exc}")

    for pdf_path in args.pdf:
        try:
            reports.append(summarize_pdf(pdf_path, manual_id=Path(pdf_path).stem, max_pages=args.max_pages))
            print(f"[OK] inspected {pdf_path}")
        except Exception as exc:
            failures.append({"manual_id": Path(pdf_path).stem, "pdf_path": pdf_path, "error": str(exc)})
            print(f"[FAIL] {pdf_path}: {type(exc).__name__}: {exc}")

    payload = {"reports": reports, "failures": failures}
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote inspection summary: {output_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
