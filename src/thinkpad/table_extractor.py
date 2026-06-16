"""Structured table extraction for ThinkPad HMM pages."""

from __future__ import annotations

import re

from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import Citation, HMMPage, TableRecord
from src.thinkpad.spike import classify_table_text

_FRU_HEADING_RE = re.compile(r"(?m)^\s*(?P<fru_id>[1-9]\d{3})\s+(?P<name>[A-Za-z][^\n]{2,120})$")


def extract_table_records(manual: ManualMetadata, pages: list[HMMPage]) -> list[TableRecord]:
    """Extract structured table rows from page table blocks and simple fixtures."""

    records: list[TableRecord] = []
    for page in pages:
        table_blocks = list(page.table_blocks)
        table_blocks.extend(_parse_markdown_tables(page.text))

        for table_index, rows in enumerate(table_blocks):
            normalized_rows = _normalize_rows(rows)
            if len(normalized_rows) < 2:
                continue

            columns = _dedupe_columns(normalized_rows[0])
            table_type = classify_table_text(_table_text(normalized_rows))
            parent_section = _find_parent_section_for_table(page.text, normalized_rows)
            citation = Citation(
                manual_id=manual.manual_id,
                source_url=manual.source_url,
                page_start=page.page,
                section=parent_section,
                section_id=_section_id(parent_section),
            )

            for row_index, row_values in enumerate(normalized_rows[1:], start=1):
                row = _row_to_dict(columns, row_values)
                if not any(value.strip() for value in row.values()):
                    continue
                records.append(
                    TableRecord(
                        record_id=(
                            f"{manual.manual_id}_p{page.page:03d}_"
                            f"t{table_index:02d}_r{row_index:03d}"
                        ),
                        manual_id=manual.manual_id,
                        page=page.page,
                        table_type=table_type,
                        columns=columns,
                        row=row,
                        citation=citation,
                        parent_section=parent_section,
                        source_url=manual.source_url,
                    )
                )
    return records


def _normalize_rows(rows: list[list[str]]) -> list[list[str]]:
    normalized: list[list[str]] = []
    for row in rows:
        cleaned = [re.sub(r"\s+", " ", str(cell or "")).strip() for cell in row]
        if any(cleaned):
            normalized.append(cleaned)
    return normalized


def _dedupe_columns(columns: list[str]) -> list[str]:
    result: list[str] = []
    seen: dict[str, int] = {}
    for index, column in enumerate(columns, start=1):
        name = column.strip() or f"column_{index}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        if count:
            name = f"{name}_{count + 1}"
        result.append(name)
    return result


def _row_to_dict(columns: list[str], values: list[str]) -> dict[str, str]:
    padded = list(values[: len(columns)])
    if len(padded) < len(columns):
        padded.extend([""] * (len(columns) - len(padded)))
    return dict(zip(columns, padded))


def _table_text(rows: list[list[str]]) -> str:
    return "\n".join("\t".join(row) for row in rows)


def _parse_markdown_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells):
                continue
            current.append(cells)
        else:
            if current:
                tables.append(current)
                current = []
    if current:
        tables.append(current)
    return tables


def _find_parent_section_for_table(text: str, rows: list[list[str]]) -> str | None:
    """Attribute a table to the nearest FRU heading that PRECEDES it.

    A page can carry several FRU sections (e.g. 1060 / 1070 / 1080 plus their
    screw tables). Taking the last heading on the page mis-attributes an earlier
    FRU's screw/torque table to a later FRU. We locate the table in the page
    text by its first non-empty cell and pick the closest heading at or before
    that offset. When the table cannot be located, fall back to the FIRST
    heading on the page (not the last), which is the safer default.
    """

    matches = list(_FRU_HEADING_RE.finditer(text))
    if not matches:
        return None

    anchor = _table_anchor_offset(text, rows)
    chosen = matches[0]
    if anchor is not None:
        preceding = [m for m in matches if m.start() <= anchor]
        if preceding:
            chosen = preceding[-1]
    name = re.sub(r"\s+", " ", chosen.group("name")).strip()
    return f"{chosen.group('fru_id')} {name}"


def _table_anchor_offset(text: str, rows: list[list[str]]) -> int | None:
    for row in rows:
        for cell in row:
            cell = cell.strip()
            if len(cell) < 4:
                continue
            index = text.find(cell)
            if index != -1:
                return index
    return None


def _section_id(section: str | None) -> str | None:
    if not section:
        return None
    match = re.match(r"^(\d{4})\b", section)
    return match.group(1) if match else None
