#!/usr/bin/env python
"""Extract structured ThinkPad HMM artifacts into local ignored JSONL files."""

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

from src.thinkpad.extraction import (  # noqa: E402
    ExtractionOptions,
    extract_manual_artifacts,
    write_jsonl,
    write_summary,
)
from src.thinkpad.manifest import ManualMetadata, load_manifest  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract local ThinkPad HMM tables, figures, FRU procedures, and warnings.",
    )
    parser.add_argument(
        "--manifest",
        default="data/manifests/manuals_manifest.yaml",
        help="Path to local manifest YAML.",
    )
    parser.add_argument(
        "--manual-id",
        action="append",
        help="Manual ID to extract. May be passed multiple times. Defaults to all manuals.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/extracted/m3",
        help="Ignored local output directory for JSONL artifacts.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional max pages per manual for quick local checks.",
    )
    parser.add_argument(
        "--write-images",
        action="store_true",
        help="Write extracted/raster images under output-dir/images. Default only records metadata.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manuals = _select_manuals(load_manifest(args.manifest), args.manual_id)
    if not manuals:
        print("[FAIL] No manuals selected")
        return 2

    options = ExtractionOptions(
        output_dir=output_dir,
        max_pages=args.max_pages,
        write_images=args.write_images,
    )

    all_tables: list[dict] = []
    all_figures: list[dict] = []
    all_fru_procedures: list[dict] = []
    all_warnings: list[dict] = []
    all_dependency_edges: list[dict] = []
    manual_summaries: list[dict] = []
    failures: list[dict] = []

    for manual in manuals:
        print(f"[*] Extracting {manual.manual_id}")
        try:
            result = extract_manual_artifacts(manual, options)
        except Exception as exc:
            failures.append({"manual_id": manual.manual_id, "error": str(exc)})
            print(f"[FAIL] {manual.manual_id}: {exc}")
            continue

        tables = [record.to_dict() for record in result.tables]
        figures = [record.to_dict() for record in result.figures]
        fru_procedures = [record.to_dict() for record in result.fru_procedures]
        warnings = [record.to_dict() for record in result.warnings]
        dependency_edges = [record.to_dict() for record in result.dependency_edges]

        all_tables.extend(tables)
        all_figures.extend(figures)
        all_fru_procedures.extend(fru_procedures)
        all_warnings.extend(warnings)
        all_dependency_edges.extend(dependency_edges)
        manual_summaries.append(
            {
                "manual_id": result.manual_id,
                "pages": result.page_count,
                "tables": len(tables),
                "figures": len(figures),
                "fru_procedures": len(fru_procedures),
                "warnings": len(warnings),
                "dependency_edges": len(dependency_edges),
            }
        )
        print(
            "[OK] "
            f"pages={result.page_count} "
            f"tables={len(tables)} "
            f"figures={len(figures)} "
            f"fru={len(fru_procedures)} "
            f"warnings={len(warnings)} "
            f"edges={len(dependency_edges)}"
        )

    write_jsonl(output_dir / "tables.jsonl", all_tables)
    write_jsonl(output_dir / "figures.jsonl", all_figures)
    write_jsonl(output_dir / "fru_procedures.jsonl", all_fru_procedures)
    write_jsonl(output_dir / "warnings.jsonl", all_warnings)
    write_jsonl(output_dir / "dependency_edges.jsonl", all_dependency_edges)

    summary = {
        "manuals": manual_summaries,
        "failures": failures,
        "totals": {
            "manuals_requested": len(manuals),
            "manuals_succeeded": len(manual_summaries),
            "manuals_failed": len(failures),
            "pages": sum(item["pages"] for item in manual_summaries),
            "tables": len(all_tables),
            "figures": len(all_figures),
            "fru_procedures": len(all_fru_procedures),
            "warnings": len(all_warnings),
            "dependency_edges": len(all_dependency_edges),
        },
    }
    write_summary(output_dir / "summary.json", summary)
    print(f"[*] Wrote extraction artifacts to {output_dir}")
    return 1 if failures else 0


def _select_manuals(manuals: list[ManualMetadata], manual_ids: list[str] | None) -> list[ManualMetadata]:
    if not manual_ids:
        return manuals
    requested = set(manual_ids)
    return [manual for manual in manuals if manual.manual_id in requested]


if __name__ == "__main__":
    raise SystemExit(main())
