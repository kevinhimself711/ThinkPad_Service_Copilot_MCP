"""Orchestration helpers for ThinkPad HMM local extraction."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from src.thinkpad.figure_extractor import extract_figure_records
from src.thinkpad.fru_extractor import extract_fru_procedures
from src.thinkpad.hmm_loader import load_hmm_pages
from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import ExtractionResult
from src.thinkpad.safety import extract_warning_records
from src.thinkpad.table_extractor import extract_table_records


@dataclass(frozen=True)
class ExtractionOptions:
    """Options for local HMM extraction without retrieval or vector upsert."""

    output_dir: str | Path = "data/extracted/m3"
    max_pages: int | None = None
    write_images: bool = False


def extract_manual_artifacts(
    manual: ManualMetadata,
    options: ExtractionOptions,
) -> ExtractionResult:
    """Extract structured local artifacts for one manifest manual."""

    pages = load_hmm_pages(manual, max_pages=options.max_pages)
    tables = extract_table_records(manual, pages)
    fru_procedures, dependency_edges = extract_fru_procedures(manual, pages)
    warnings = extract_warning_records(manual, pages)
    figures = extract_figure_records(
        manual=manual,
        pdf_path=manual.local_pdf_path,
        pages=pages,
        output_dir=Path(options.output_dir) / "images",
        write_images=options.write_images,
    )
    return ExtractionResult(
        manual_id=manual.manual_id,
        page_count=len(pages),
        tables=tables,
        figures=figures,
        fru_procedures=fru_procedures,
        warnings=warnings,
        dependency_edges=dependency_edges,
    )


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> None:
    """Write JSONL rows with deterministic UTF-8 serialization."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def write_summary(path: str | Path, payload: dict) -> None:
    """Write a JSON summary file."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
