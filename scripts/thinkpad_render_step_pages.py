#!/usr/bin/env python
"""Read-only annotation aid: dump candidate step pages as plain text.

Given a step-citation review pack, this prints, for each candidate step, the
plain text of its candidate PDF page (and optional neighbors) so a human
reviewer can eyeball whether the step label belongs to that page. It only
reads local PDFs and never writes verified pages or copies prose into any
committed artifact. Delete after annotation if desired.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))


def _configure_windows_stdio() -> None:
    if sys.platform != "win32":
        return
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render candidate step pages for human review.")
    parser.add_argument("--pack", default="data/eval/m8_5_step_citation_review.json")
    parser.add_argument("--neighbors", type=int, default=1, help="Pages to show on each side.")
    parser.add_argument("--chars", type=int, default=600, help="Max chars of page text to print.")
    parser.add_argument("--case-id", default=None, help="Limit to a single case_id.")
    return parser.parse_args()


def main() -> int:
    _configure_windows_stdio()
    args = parse_args()
    try:
        import fitz  # type: ignore  # noqa: F401
    except ImportError:
        print("PyMuPDF (pymupdf) is required to render pages.", file=sys.stderr)
        return 2

    pack_path = Path(args.pack)
    if not pack_path.exists():
        print(f"Review pack not found: {pack_path}", file=sys.stderr)
        return 2
    pack = json.loads(pack_path.read_text(encoding="utf-8"))

    doc_cache: dict[str, Any] = {}
    for candidate in pack.get("candidates", []):
        if args.case_id and candidate.get("case_id") != args.case_id:
            continue
        _render_candidate(candidate, doc_cache, args.neighbors, args.chars)

    for doc in doc_cache.values():
        if doc is not None:
            doc.close()
    return 0


def _render_candidate(
    candidate: dict[str, Any],
    doc_cache: dict[str, Any],
    neighbors: int,
    chars: int,
) -> None:
    import fitz  # type: ignore

    pdf_path = candidate.get("pdf_local_path")
    print("=" * 88)
    print(f"CASE {candidate.get('case_id')}  [{candidate.get('category')}]")
    print(f"FRU {candidate.get('fru_id')} {candidate.get('fru_name')}  PDF={pdf_path}")
    if not pdf_path or not Path(pdf_path).exists():
        print(f"  [skip] PDF missing: {pdf_path}")
        return
    if pdf_path not in doc_cache:
        try:
            doc_cache[pdf_path] = fitz.open(pdf_path)
        except Exception as exc:  # noqa: BLE001
            doc_cache[pdf_path] = None
            print(f"  [skip] cannot open PDF: {exc}")
            return
    doc = doc_cache[pdf_path]
    if doc is None:
        return

    for step in candidate.get("candidate_steps") or []:
        page = step.get("candidate_page")
        print("-" * 88)
        print(
            f"  step_index={step.get('step_index')}  candidate_page={page}  "
            f"quality={step.get('label_quality')}"
        )
        print(f"  label: {step.get('step_label')}")
        if not isinstance(page, int):
            print("  [no candidate_page]")
            continue
        for p in range(page - neighbors, page + neighbors + 1):
            index = p - 1
            if index < 0 or index >= doc.page_count:
                continue
            text = " ".join(doc[index].get_text("text").split())
            tag = " <== candidate" if p == page else ""
            print(f"    [PDF page {p}]{tag}: {text[:chars]}")


if __name__ == "__main__":
    raise SystemExit(main())
