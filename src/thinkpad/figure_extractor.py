"""Figure and raster-fallback extraction for ThinkPad HMM pages."""

from __future__ import annotations

import re
from pathlib import Path

from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import Citation, FigureRecord, HMMPage


def extract_figure_records(
    manual: ManualMetadata,
    pdf_path: str | Path,
    pages: list[HMMPage],
    output_dir: str | Path,
    write_images: bool = False,
) -> list[FigureRecord]:
    """Extract figure records from embedded images and vector drawing signals."""

    output_path = Path(output_dir)
    records: list[FigureRecord] = []
    doc = None
    if write_images:
        try:
            import fitz  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required when write_images=True") from exc
        output_path.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(Path(pdf_path))

    try:
        for page in pages:
            citation = Citation(
                manual_id=manual.manual_id,
                source_url=manual.source_url,
                page_start=page.page,
            )
            surrounding_text = _surrounding_text(page.text)

            for image_index in range(max(page.embedded_image_count, 0)):
                image_id = f"{manual.manual_id}_p{page.page:03d}_img{image_index + 1:02d}"
                storage_uri = None
                if write_images and doc is not None:
                    storage_uri = _write_embedded_image(doc, page, image_index, image_id, output_path)
                records.append(
                    FigureRecord(
                        image_id=image_id,
                        manual_id=manual.manual_id,
                        page=page.page,
                        citation=citation,
                        caption="Embedded HMM image candidate",
                        surrounding_text=surrounding_text,
                        storage_uri=storage_uri,
                        source_url=manual.source_url,
                    )
                )

            if page.raster_fallback_needed:
                image_id = f"{manual.manual_id}_p{page.page:03d}_raster"
                storage_uri = None
                if write_images and doc is not None:
                    storage_uri = _write_page_raster(doc, page.page, image_id, output_path)
                records.append(
                    FigureRecord(
                        image_id=image_id,
                        manual_id=manual.manual_id,
                        page=page.page,
                        citation=citation,
                        caption="Raster fallback candidate for vector line drawing",
                        surrounding_text=surrounding_text,
                        storage_uri=storage_uri,
                        source_url=manual.source_url,
                    )
                )
    finally:
        if doc is not None:
            doc.close()

    return records


def _write_embedded_image(doc, page: HMMPage, image_index: int, image_id: str, output_dir: Path) -> str | None:
    if image_index >= len(page.image_xrefs):
        return None
    image = doc.extract_image(page.image_xrefs[image_index])
    extension = image.get("ext", "png")
    image_path = output_dir / f"{image_id}.{extension}"
    image_path.write_bytes(image["image"])
    return str(image_path)


def _write_page_raster(doc, page_number: int, image_id: str, output_dir: Path) -> str:
    page = doc[page_number - 1]
    pixmap = page.get_pixmap()
    image_path = output_dir / f"{image_id}.png"
    pixmap.save(image_path)
    return str(image_path)


def _surrounding_text(text: str, limit: int = 600) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]
