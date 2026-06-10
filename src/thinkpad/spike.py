"""Lightweight HMM PDF inspection helpers for the M1 risk spike."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

FRU_HEADING_RE = re.compile(r"(?m)^\s*(?P<fru_id>\d{4})\s+(?P<name>[A-Za-z][^\n]{2,120})$")
SAFETY_RE = re.compile(r"\b(DANGER|CAUTION|Attention|ESD|battery|batteries|system board)\b", re.I)
FRU_REF_RE = re.compile(r"\b(?P<fru_id>\d{4})\s+(?P<name>[A-Za-z][A-Za-z0-9 .()&+-]{2,80})")


@dataclass(frozen=True)
class TableCandidate:
    """A page-level table candidate used to assess row-preservation risk."""

    page: int
    table_type: str
    method: str
    row_count: int | None = None
    column_count: int | None = None


@dataclass(frozen=True)
class FigureCandidate:
    """A page-level figure signal for embedded-image and raster fallback checks."""

    page: int
    embedded_image_count: int
    drawing_count: int
    raster_fallback_needed: bool


@dataclass(frozen=True)
class FRUSectionCandidate:
    """A candidate FRU procedure section and its prerequisite signals."""

    fru_id: str
    fru_name: str
    page: int | None = None
    prerequisites: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SafetyWarningCandidate:
    """A page-level safety warning signal."""

    page: int
    warning_level: str
    keyword: str


def compute_sha256(path: str | Path) -> str:
    """Compute a streaming SHA256 digest for a local file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_table_text(text: str) -> str:
    """Classify a table-like text block into the ThinkPad HMM risk categories."""

    lowered = text.lower()
    if re.search(r"\berror\s+code\b|\bsymptom\b|\bdiagnostic\b", lowered):
        return "error_code"
    if "torque" in lowered or re.search(r"\bm\d(?:\.\d)?\s*x\s*\d", lowered):
        return "screw_spec"
    if re.search(r"\bfru\b|field replaceable unit|part no\.?|part number", lowered):
        return "fru"
    if re.search(r"\bcode\b.*\baction\b|\btest\b.*\bresult\b", lowered, flags=re.DOTALL):
        return "diagnostic"
    return "unknown"


def extract_prerequisites(text: str) -> list[str]:
    """Extract prerequisite FRU references from a procedure text block."""

    lowered = text.lower()
    prerequisite_window = text
    markers = [
        "before removing",
        "before you remove",
        "for access, remove",
        "remove the following",
        "prerequisite",
    ]
    positions = [lowered.find(marker) for marker in markers if lowered.find(marker) >= 0]
    if positions:
        start = min(positions)
        prerequisite_window = text[start : start + 1000]

    prerequisites: list[str] = []
    seen: set[str] = set()
    for match in FRU_REF_RE.finditer(prerequisite_window):
        value = f"{match.group('fru_id')} {match.group('name').strip()}"
        value = re.sub(r"\s+", " ", value).strip(" .;,")
        if value not in seen:
            seen.add(value)
            prerequisites.append(value)
    return prerequisites


def find_fru_sections(text: str, page: int | None = None) -> list[FRUSectionCandidate]:
    """Find FRU section headings and nearby prerequisite references."""

    candidates: list[FRUSectionCandidate] = []
    matches = list(FRU_HEADING_RE.finditer(text))
    valid_matches = []
    for match in matches:
        prior_lines = [line.strip().lower() for line in text[: match.start()].splitlines() if line.strip()]
        previous_line = prior_lines[-1] if prior_lines else ""
        if "following frus" in previous_line or "remove these frus" in previous_line:
            continue
        valid_matches.append(match)

    for index, match in enumerate(valid_matches):
        start = match.end()
        end = (
            valid_matches[index + 1].start()
            if index + 1 < len(valid_matches)
            else min(len(text), start + 2000)
        )
        section_text = text[start:end]
        candidates.append(
            FRUSectionCandidate(
                fru_id=match.group("fru_id"),
                fru_name=re.sub(r"\s+", " ", match.group("name")).strip(),
                page=page,
                prerequisites=extract_prerequisites(section_text),
            )
        )
    return candidates


def find_safety_warnings(text: str, page: int) -> list[SafetyWarningCandidate]:
    """Detect page-level safety warning markers without storing full copyrighted text."""

    warnings: list[SafetyWarningCandidate] = []
    seen: set[tuple[str, str]] = set()
    for match in SAFETY_RE.finditer(text):
        keyword = match.group(1)
        warning_level = "DANGER" if keyword.upper() == "DANGER" else "CAUTION"
        if keyword.lower() in {"battery", "batteries", "system board"}:
            warning_level = "SAFETY_RELATED"
        key = (warning_level, keyword.lower())
        if key in seen:
            continue
        seen.add(key)
        warnings.append(SafetyWarningCandidate(page=page, warning_level=warning_level, keyword=keyword))
    return warnings


def summarize_pdf(
    pdf_path: str | Path,
    *,
    manual_id: str | None = None,
    max_pages: int | None = None,
) -> dict[str, Any]:
    """Inspect a local PDF and return M1 spike summary counts.

    The returned payload avoids full extracted text and keeps only aggregate
    counts plus short structural candidates.
    """

    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required for PDF spike inspection") from exc

    path = Path(pdf_path)
    doc = fitz.open(path)
    page_count = len(doc)
    pages_to_scan = page_count if max_pages is None else min(page_count, max_pages)

    table_candidates: list[TableCandidate] = []
    figure_candidates: list[FigureCandidate] = []
    fru_sections: list[FRUSectionCandidate] = []
    safety_warnings: list[SafetyWarningCandidate] = []
    title_lines: list[str] = []
    pages_with_text = 0

    for page_index in range(pages_to_scan):
        page = doc[page_index]
        page_number = page_index + 1
        text = page.get_text("text") or ""
        if text.strip():
            pages_with_text += 1
        if page_index < 3:
            title_lines.extend(line.strip() for line in text.splitlines() if line.strip())

        table_type = classify_table_text(text)
        if table_type != "unknown":
            table_candidates.append(
                TableCandidate(page=page_number, table_type=table_type, method="text_heuristic")
            )

        if hasattr(page, "find_tables"):
            try:
                tables = page.find_tables()
                for table in getattr(tables, "tables", []):
                    rows = table.extract()
                    table_text = "\n".join("\t".join(cell or "" for cell in row) for row in rows)
                    table_candidates.append(
                        TableCandidate(
                            page=page_number,
                            table_type=classify_table_text(table_text),
                            method="pymupdf_find_tables",
                            row_count=len(rows),
                            column_count=max((len(row) for row in rows), default=0),
                        )
                    )
            except Exception:
                table_candidates.append(
                    TableCandidate(page=page_number, table_type="unknown", method="pymupdf_find_tables_failed")
                )

        embedded_images = len(page.get_images(full=True))
        try:
            drawings = len(page.get_drawings())
        except Exception:
            drawings = 0
        if embedded_images or drawings:
            figure_candidates.append(
                FigureCandidate(
                    page=page_number,
                    embedded_image_count=embedded_images,
                    drawing_count=drawings,
                    raster_fallback_needed=embedded_images == 0 and drawings > 0,
                )
            )

        fru_sections.extend(find_fru_sections(text, page=page_number))
        safety_warnings.extend(find_safety_warnings(text, page_number))

    doc.close()

    return {
        "manual_id": manual_id,
        "pdf_path": str(path),
        "sha256": compute_sha256(path),
        "file_size_bytes": path.stat().st_size,
        "page_count": page_count,
        "pages_scanned": pages_to_scan,
        "pages_with_text": pages_with_text,
        "title_candidates": title_lines[:8],
        "table_candidates": [asdict(candidate) for candidate in table_candidates],
        "figure_candidates": [asdict(candidate) for candidate in figure_candidates],
        "fru_section_candidates": [asdict(candidate) for candidate in fru_sections],
        "safety_warning_candidates": [asdict(candidate) for candidate in safety_warnings],
        "counts": {
            "table_candidates": len(table_candidates),
            "figure_candidates": len(figure_candidates),
            "fru_section_candidates": len(fru_sections),
            "safety_warning_candidates": len(safety_warnings),
            "raster_fallback_pages": sum(1 for candidate in figure_candidates if candidate.raster_fallback_needed),
        },
    }
