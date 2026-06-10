"""Build citation-backed ThinkPad retrieval chunks from M3 extraction JSONL."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.types import Chunk
from src.thinkpad.manifest import ManualMetadata


class RetrievalCorpusError(RuntimeError):
    """Raised when local ThinkPad retrieval corpus construction fails."""


@dataclass(frozen=True)
class ThinkPadRetrievalChunk:
    """One retrieval-ready record rendered from a structured HMM extraction artifact."""

    chunk_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_chunk(self) -> Chunk:
        """Convert to the upstream Chunk contract."""

        return Chunk(id=self.chunk_id, text=self.text, metadata=self.metadata)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "id": self.chunk_id,
            "text": self.text,
            "metadata": self.metadata,
        }


def build_retrieval_chunks(
    extracted_dir: str | Path,
    manuals: list[ManualMetadata],
    limit: int | None = None,
) -> list[ThinkPadRetrievalChunk]:
    """Render M3 extraction JSONL files into retrieval chunks."""

    root = Path(extracted_dir)
    if not root.exists():
        raise RetrievalCorpusError(f"extracted_dir does not exist: {root}")

    manual_by_id = {manual.manual_id: manual for manual in manuals}
    chunks: list[ThinkPadRetrievalChunk] = []
    chunks.extend(_build_table_chunks(root / "tables.jsonl", manual_by_id))
    chunks.extend(_build_fru_chunks(root / "fru_procedures.jsonl", manual_by_id))
    chunks.extend(_build_warning_chunks(root / "warnings.jsonl", manual_by_id))
    chunks.extend(_build_figure_chunks(root / "figures.jsonl", manual_by_id))

    chunks = [chunk for chunk in chunks if chunk.text.strip()]
    chunks.sort(key=lambda chunk: chunk.chunk_id)
    return chunks[:limit] if limit is not None else chunks


def chunks_to_core(chunks: Iterable[ThinkPadRetrievalChunk]) -> list[Chunk]:
    """Convert ThinkPad retrieval chunks to upstream core chunks."""

    return [chunk.to_chunk() for chunk in chunks]


def _build_table_chunks(
    path: Path,
    manual_by_id: dict[str, ManualMetadata],
) -> list[ThinkPadRetrievalChunk]:
    chunks: list[ThinkPadRetrievalChunk] = []
    for record in _read_jsonl(path):
        manual = _manual_for(record, manual_by_id)
        row = record.get("row") or {}
        columns = record.get("columns") or []
        row_text = "; ".join(f"{column}: {row.get(column, '')}" for column in columns)
        text = "\n".join(
            _clean_lines(
                [
                    f"ThinkPad HMM table row: {record.get('table_type', 'unknown')}",
                    f"Manual: {manual.title}",
                    f"Models: {', '.join(manual.models)}",
                    f"Generations: {', '.join(manual.generations)}",
                    f"Machine types: {', '.join(manual.machine_types)}",
                    f"Page: {record.get('page')}",
                    f"Parent section: {record.get('parent_section')}",
                    f"Columns: {', '.join(columns)}",
                    f"Row: {row_text}",
                ]
            )
        )
        chunks.append(
            ThinkPadRetrievalChunk(
                chunk_id=f"table::{record['record_id']}",
                text=text,
                metadata=_base_metadata(record, manual, "table", path)
                | {
                    "table_type": record.get("table_type", "unknown"),
                    "parent_section": record.get("parent_section"),
                    "source_record_id": record.get("record_id"),
                },
            )
        )
    return chunks


def _build_fru_chunks(
    path: Path,
    manual_by_id: dict[str, ManualMetadata],
) -> list[ThinkPadRetrievalChunk]:
    chunks: list[ThinkPadRetrievalChunk] = []
    for record in _read_jsonl(path):
        manual = _manual_for(record, manual_by_id)
        steps = [str(step) for step in record.get("steps") or []]
        prerequisites = [str(item) for item in record.get("prerequisites") or []]
        text = "\n".join(
            _clean_lines(
                [
                    f"ThinkPad HMM FRU procedure: {record.get('fru_id')} {record.get('fru_name')}",
                    f"Manual: {manual.title}",
                    f"Models: {', '.join(manual.models)}",
                    f"Generations: {', '.join(manual.generations)}",
                    f"Machine types: {', '.join(manual.machine_types)}",
                    f"Pages: {record.get('page_start')} - {record.get('page_end')}",
                    f"Prerequisites: {', '.join(prerequisites)}",
                    f"Steps: {' | '.join(steps[:40])}",
                ]
            )
        )
        chunks.append(
            ThinkPadRetrievalChunk(
                chunk_id=f"fru::{record['procedure_id']}",
                text=text,
                metadata=_base_metadata(record, manual, "fru_procedure", path)
                | {
                    "fru_id": record.get("fru_id"),
                    "fru_name": record.get("fru_name"),
                    "section_id": record.get("fru_id"),
                    "source_record_id": record.get("procedure_id"),
                },
            )
        )
    return chunks


def _build_warning_chunks(
    path: Path,
    manual_by_id: dict[str, ManualMetadata],
) -> list[ThinkPadRetrievalChunk]:
    chunks: list[ThinkPadRetrievalChunk] = []
    for record in _read_jsonl(path):
        manual = _manual_for(record, manual_by_id)
        text = "\n".join(
            _clean_lines(
                [
                    f"ThinkPad HMM safety warning: {record.get('warning_level')}",
                    f"Manual: {manual.title}",
                    f"Models: {', '.join(manual.models)}",
                    f"Generations: {', '.join(manual.generations)}",
                    f"Machine types: {', '.join(manual.machine_types)}",
                    f"Page: {record.get('page')}",
                    f"Related component: {record.get('related_component')}",
                    f"Warning text: {record.get('text')}",
                ]
            )
        )
        chunks.append(
            ThinkPadRetrievalChunk(
                chunk_id=f"warning::{record['warning_id']}",
                text=text,
                metadata=_base_metadata(record, manual, "warning", path)
                | {
                    "warning_level": record.get("warning_level"),
                    "related_component": record.get("related_component"),
                    "source_record_id": record.get("warning_id"),
                },
            )
        )
    return chunks


def _build_figure_chunks(
    path: Path,
    manual_by_id: dict[str, ManualMetadata],
) -> list[ThinkPadRetrievalChunk]:
    chunks: list[ThinkPadRetrievalChunk] = []
    for record in _read_jsonl(path):
        manual = _manual_for(record, manual_by_id)
        text = "\n".join(
            _clean_lines(
                [
                    f"ThinkPad HMM figure candidate: {record.get('caption')}",
                    f"Manual: {manual.title}",
                    f"Models: {', '.join(manual.models)}",
                    f"Generations: {', '.join(manual.generations)}",
                    f"Machine types: {', '.join(manual.machine_types)}",
                    f"Page: {record.get('page')}",
                    f"Related FRU: {record.get('related_fru_id')}",
                    f"Related component: {record.get('related_component')}",
                    f"Surrounding text: {record.get('surrounding_text')}",
                ]
            )
        )
        chunks.append(
            ThinkPadRetrievalChunk(
                chunk_id=f"figure::{record['image_id']}",
                text=text,
                metadata=_base_metadata(record, manual, "figure", path)
                | {
                    "image_id": record.get("image_id"),
                    "related_fru_id": record.get("related_fru_id"),
                    "related_component": record.get("related_component"),
                    "source_record_id": record.get("image_id"),
                },
            )
        )
    return chunks


def _base_metadata(
    record: dict[str, Any],
    manual: ManualMetadata,
    record_type: str,
    source_path: Path,
) -> dict[str, Any]:
    citation = record.get("citation") or {}
    page_start = citation.get("page_start") or record.get("page_start") or record.get("page")
    page_end = citation.get("page_end") or record.get("page_end") or page_start
    return {
        "source_path": str(source_path).replace("\\", "/"),
        "source_url": citation.get("source_url") or record.get("source_url") or manual.source_url,
        "manual_id": manual.manual_id,
        "manual_title": manual.title,
        "record_type": record_type,
        "models": ",".join(manual.models),
        "generations": ",".join(manual.generations),
        "machine_types": ",".join(manual.machine_types),
        "page_start": int(page_start) if page_start is not None else 0,
        "page_end": int(page_end) if page_end is not None else 0,
        "section": citation.get("section"),
        "section_id": citation.get("section_id"),
        "collection": "thinkpad",
        "doc_type": "thinkpad_hmm_record",
    }


def _manual_for(record: dict[str, Any], manual_by_id: dict[str, ManualMetadata]) -> ManualMetadata:
    manual_id = record.get("manual_id")
    if manual_id not in manual_by_id:
        raise RetrievalCorpusError(f"record references unknown manual_id: {manual_id}")
    return manual_by_id[manual_id]


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise RetrievalCorpusError(f"invalid JSONL at {path}:{line_number}") from exc


def _clean_lines(lines: Iterable[str | None]) -> list[str]:
    return [line for line in lines if line and not line.endswith(": None") and not line.endswith(": ")]
