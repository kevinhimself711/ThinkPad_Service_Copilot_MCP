"""Safety warning extraction for ThinkPad HMM pages."""

from __future__ import annotations

import re

from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import Citation, HMMPage, WarningRecord

_SAFETY_RE = re.compile(r"\b(DANGER|CAUTION|Attention|ESD|battery|batteries|system board)\b", re.I)


def extract_warning_records(manual: ManualMetadata, pages: list[HMMPage]) -> list[WarningRecord]:
    """Extract cited page-level safety warning records."""

    records: list[WarningRecord] = []
    for page in pages:
        if _is_toc_or_index_page(page.text):
            continue
        seen: set[tuple[str, str]] = set()
        for match in _SAFETY_RE.finditer(page.text):
            keyword = match.group(1)
            warning_level = _warning_level(keyword)
            key = (warning_level, keyword.lower())
            if key in seen:
                continue
            seen.add(key)
            citation = Citation(
                manual_id=manual.manual_id,
                source_url=manual.source_url,
                page_start=page.page,
            )
            records.append(
                WarningRecord(
                    warning_id=(
                        f"{manual.manual_id}_p{page.page:03d}_"
                        f"{warning_level.lower()}_{len(records):04d}"
                    ),
                    manual_id=manual.manual_id,
                    warning_level=warning_level,
                    text=_context(page.text, match.start(), match.end()),
                    citation=citation,
                    page=page.page,
                    related_component=_related_component(keyword),
                )
            )
    return records


def _warning_level(keyword: str) -> str:
    upper = keyword.upper()
    if upper == "DANGER":
        return "DANGER"
    if keyword.lower() in {"battery", "batteries", "system board"}:
        return "SAFETY_RELATED"
    return "CAUTION"


def _related_component(keyword: str) -> str | None:
    lowered = keyword.lower()
    if lowered in {"battery", "batteries"}:
        return "battery"
    if lowered == "system board":
        return "system board"
    if lowered == "esd":
        return "ESD"
    return None


def _is_toc_or_index_page(text: str) -> bool:
    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    first = lines[0]
    if first not in {"contents", "table of contents", "index"}:
        return False
    dotted_leaders = len(re.findall(r"\.\s*\.\s*\.", text))
    chapter_refs = len(re.findall(r"\bchapter\s+\d+\b", text, re.I))
    return dotted_leaders >= 3 or chapter_refs >= 2


def _context(text: str, start: int, end: int, radius: int = 160) -> str:
    snippet = text[max(0, start - radius) : min(len(text), end + radius)]
    return re.sub(r"\s+", " ", snippet).strip()
