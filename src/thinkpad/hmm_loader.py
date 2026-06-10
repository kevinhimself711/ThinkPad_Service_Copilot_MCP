"""Local ThinkPad HMM PDF loader with integrity checks and page signals."""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import HMMPage


class HMMExtractionError(RuntimeError):
    """Raised when local HMM extraction cannot safely proceed."""


def load_hmm_pages(
    manual: ManualMetadata,
    pdf_path: str | Path | None = None,
    max_pages: int | None = None,
) -> list[HMMPage]:
    """Load local HMM pages and structural signals from a PDF.

    Missing files and integrity mismatches are hard errors. This function does
    not download files or mutate the manifest.
    """

    path = Path(pdf_path or manual.local_pdf_path)
    _verify_local_pdf(manual, path)

    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise HMMExtractionError("PyMuPDF is required for HMM page loading") from exc

    doc = fitz.open(path)
    try:
        page_count = len(doc)
        pages_to_load = page_count if max_pages is None else min(page_count, max_pages)
        pages: list[HMMPage] = []

        for page_index in range(pages_to_load):
            page = doc[page_index]
            page_number = page_index + 1
            page_text = page.get_text("text") or ""
            image_entries = page.get_images(full=True)
            image_xrefs = [int(entry[0]) for entry in image_entries if entry]
            try:
                drawing_count = len(page.get_drawings())
            except Exception:
                drawing_count = 0

            table_blocks: list[list[list[str]]] = []
            if hasattr(page, "find_tables") and _should_probe_tables(page_text):
                try:
                    tables = page.find_tables()
                    for table in getattr(tables, "tables", []):
                        rows = table.extract()
                        table_blocks.append([[cell or "" for cell in row] for row in rows])
                except Exception:
                    table_blocks = []

            rect = page.rect
            pages.append(
                HMMPage(
                    manual_id=manual.manual_id,
                    page=page_number,
                    text=page_text,
                    source_url=manual.source_url,
                    embedded_image_count=len(image_entries),
                    drawing_count=drawing_count,
                    raster_fallback_needed=len(image_entries) == 0 and drawing_count > 0,
                    width=float(rect.width),
                    height=float(rect.height),
                    table_blocks=table_blocks,
                    image_xrefs=image_xrefs,
                )
            )
        return pages
    finally:
        doc.close()


def _verify_local_pdf(manual: ManualMetadata, path: Path) -> None:
    if not path.exists():
        raise HMMExtractionError(f"{manual.manual_id}: local PDF does not exist: {path}")
    if not path.is_file():
        raise HMMExtractionError(f"{manual.manual_id}: local PDF path is not a file: {path}")

    if manual.spike_status in {"downloaded", "validated"}:
        if manual.file_size_bytes is not None and path.stat().st_size != manual.file_size_bytes:
            raise HMMExtractionError(
                f"{manual.manual_id}: file size mismatch "
                f"(expected {manual.file_size_bytes}, got {path.stat().st_size})"
            )
        if manual.checksum_sha256 is not None:
            actual = _compute_sha256(path)
            if actual.lower() != manual.checksum_sha256.lower():
                raise HMMExtractionError(
                    f"{manual.manual_id}: checksum mismatch "
                    f"(expected {manual.checksum_sha256}, got {actual})"
            )


def _should_probe_tables(text: str) -> bool:
    lower = text.lower()
    table_keywords = (
        "error code",
        "symptom or error",
        "fru no",
        "fru no.",
        "fru part",
        "cru id",
        "part no",
        "part number",
        "field replaceable unit",
        "screw",
        "torque",
        "parts list",
        "numeric error",
        "beep symptom",
        "specification",
    )
    if any(keyword in lower for keyword in table_keywords):
        return True

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    column_like_lines = 0
    for line in lines:
        if "\t" in line:
            column_like_lines += 1
        elif "  " in line and len(line.split()) >= 3:
            column_like_lines += 1
        if column_like_lines >= 3:
            return True
    return False


def _compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
