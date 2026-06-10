"""FRU procedure and prerequisite extraction for ThinkPad HMM pages."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import Citation, DependencyEdge, FRUProcedure, HMMPage

_FRU_HEADING_RE = re.compile(r"(?m)^\s*(?P<fru_id>\d{4})\s+(?P<name>[A-Za-z][^\n]{2,120})$")
_FRU_REF_RE = re.compile(r"\b(?P<fru_id>[1-9]\d{3})\s+(?P<name>[A-Za-z][A-Za-z0-9 .()&+-]{2,100})")
_PROCEDURE_MARKERS = (
    "removal steps",
    "before removing",
    "before you remove",
    "remove the following",
    "for access, remove",
    "when installing",
)


@dataclass(frozen=True)
class _Section:
    fru_id: str
    fru_name: str
    page_start: int
    page_end: int
    text: str


def extract_fru_procedures(
    manual: ManualMetadata,
    pages: list[HMMPage],
) -> tuple[list[FRUProcedure], list[DependencyEdge]]:
    """Extract FRU procedure records and prerequisite dependency edges."""

    sections = _find_sections(pages)
    procedures: list[FRUProcedure] = []
    edges: list[DependencyEdge] = []

    for section in sections:
        prerequisites = extract_prerequisites(section.text)
        citation = Citation(
            manual_id=manual.manual_id,
            source_url=manual.source_url,
            page_start=section.page_start,
            page_end=section.page_end,
            section=f"{section.fru_id} {section.fru_name}",
            section_id=section.fru_id,
        )
        procedures.append(
            FRUProcedure(
                procedure_id=f"{manual.manual_id}_fru_{section.fru_id}",
                manual_id=manual.manual_id,
                fru_id=section.fru_id,
                fru_name=section.fru_name,
                citation=citation,
                steps=_extract_steps(section.text),
                prerequisites=prerequisites,
                page_start=section.page_start,
                page_end=section.page_end,
            )
        )

        for prerequisite in prerequisites:
            required_fru_id = prerequisite.split(" ", 1)[0]
            edges.append(
                DependencyEdge(
                    manual_id=manual.manual_id,
                    source_fru_id=section.fru_id,
                    required_fru_id=required_fru_id,
                    citation=citation,
                )
            )

    return procedures, edges


def extract_prerequisites(text: str) -> list[str]:
    """Extract prerequisite FRU references from a procedure section."""

    lowered = text.lower()
    starts = [
        lowered.find(marker)
        for marker in ("before removing", "before you remove", "for access, remove", "remove the following")
        if lowered.find(marker) >= 0
    ]
    if not starts:
        return []
    window = text[min(starts) : min(starts) + 1400]

    prerequisites: list[str] = []
    seen: set[str] = set()
    for match in _FRU_REF_RE.finditer(window):
        fru_id = match.group("fru_id")
        if not _looks_like_fru_id(fru_id):
            continue
        value = f"{fru_id} {_clean_name(match.group('name'))}"
        if value not in seen:
            seen.add(value)
            prerequisites.append(value)
    return prerequisites


def _find_sections(pages: list[HMMPage]) -> list[_Section]:
    combined, page_offsets = _combine_pages(pages)
    heading_matches = [
        match
        for match in _FRU_HEADING_RE.finditer(combined)
        if _looks_like_fru_id(match.group("fru_id"))
        and not _is_prerequisite_list_item(combined, match.start())
    ]

    sections: list[_Section] = []
    for index, match in enumerate(heading_matches):
        start = match.start()
        end = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(combined)
        text = combined[start:end].strip()
        if not _looks_like_procedure(text):
            continue
        sections.append(
            _Section(
                fru_id=match.group("fru_id"),
                fru_name=_clean_name(match.group("name")),
                page_start=_page_for_offset(start, page_offsets),
                page_end=_page_for_offset(max(start, end - 1), page_offsets),
                text=text,
            )
        )
    return sections


def _combine_pages(pages: list[HMMPage]) -> tuple[str, list[tuple[int, int]]]:
    chunks: list[str] = []
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for page in pages:
        marker = f"\n\n[[PAGE {page.page}]]\n"
        chunks.append(marker)
        cursor += len(marker)
        offsets.append((cursor, page.page))
        chunks.append(page.text)
        cursor += len(page.text)
    return "".join(chunks), offsets


def _page_for_offset(offset: int, page_offsets: list[tuple[int, int]]) -> int:
    current = page_offsets[0][1] if page_offsets else 1
    for start, page in page_offsets:
        if start > offset:
            break
        current = page
    return current


def _looks_like_fru_id(fru_id: str) -> bool:
    return int(fru_id) >= 1000


def _looks_like_procedure(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _PROCEDURE_MARKERS)


def _is_prerequisite_list_item(text: str, start: int) -> bool:
    prior_lines = [line.strip().lower() for line in text[:start].splitlines() if line.strip()]
    previous_line = prior_lines[-1] if prior_lines else ""
    return "following frus" in previous_line or "remove these frus" in previous_line


def _extract_steps(text: str) -> list[str]:
    lines = [_clean_name(line) for line in text.splitlines()]
    steps: list[str] = []
    in_steps = False
    for line in lines:
        lowered = line.lower()
        if "removal steps" in lowered:
            in_steps = True
            continue
        if not in_steps:
            continue
        if not line or _FRU_HEADING_RE.match(line):
            continue
        if lowered.startswith(("before removing", "before you remove", "remove the following")):
            continue
        steps.append(line)
    return steps[:50]


def _clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .;,")
