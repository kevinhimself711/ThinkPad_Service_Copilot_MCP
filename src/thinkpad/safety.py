"""Safety warning extraction for ThinkPad HMM pages."""

from __future__ import annotations

import re

from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import Citation, HMMPage, WarningRecord

_SAFETY_RE = re.compile(r"\b(DANGER|CAUTION|Attention|ESD|battery|batteries|system board)\b", re.I)
# Keywords that are themselves an explicit warning trigger.
_EXPLICIT_TRIGGERS = {"danger", "caution", "attention"}
# Bare component keywords (battery / system board / ESD) appear constantly in
# ordinary prose ("disconnect the battery connector"). They only denote a real
# safety warning when the surrounding context carries an explicit warning
# trigger or a safety imperative (AGENTS.md section 6.6).
_SAFETY_TRIGGER_RE = re.compile(
    r"\b(danger|caution|attention|warning|must not|must be|do not|never|"
    r"could (ignite|explode|cause)|risk of|electrostatic)\b",
    re.I,
)


def extract_warning_records(manual: ManualMetadata, pages: list[HMMPage]) -> list[WarningRecord]:
    """Extract cited page-level safety warning records."""

    records: list[WarningRecord] = []
    for page in pages:
        if _is_toc_or_index_page(page.text):
            continue
        seen: set[tuple[str, str]] = set()
        for match in _SAFETY_RE.finditer(page.text):
            keyword = match.group(1)
            context = _context(page.text, match.start(), match.end())
            if not _is_real_warning(keyword, context):
                continue
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
                    text=context,
                    citation=citation,
                    page=page.page,
                    related_component=_related_component(keyword),
                )
            )
    return records


def _is_real_warning(keyword: str, context: str) -> bool:
    """A keyword denotes a real warning when it is itself an explicit trigger
    (DANGER/CAUTION/Attention) or when its context carries a safety trigger or
    imperative. Bare component keywords in ordinary prose are rejected.
    """

    if keyword.lower() in _EXPLICIT_TRIGGERS:
        return True
    return bool(_SAFETY_TRIGGER_RE.search(context))


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
