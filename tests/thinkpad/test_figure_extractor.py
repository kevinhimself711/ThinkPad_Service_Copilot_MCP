from pathlib import Path

from src.thinkpad.figure_extractor import extract_figure_records
from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import HMMPage


def _manual() -> ManualMetadata:
    return ManualMetadata.from_mapping(
        {
            "manual_id": "thinkpad_p1_gen4_hmm",
            "title": "ThinkPad P1 Gen 4 Hardware Maintenance Manual",
            "models": ["ThinkPad P1 Gen 4"],
            "generations": ["Gen 4"],
            "machine_types": ["20Y3"],
            "source_type": "lenovo_official",
            "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/p1_hmm.pdf",
            "local_pdf_path": "data/manuals/p1_hmm.pdf",
        }
    )


def test_extract_figure_records_marks_raster_fallback_without_writing_images():
    page = HMMPage(
        manual_id="thinkpad_p1_gen4_hmm",
        page=72,
        text="Removal steps of the thermal fan assembly. See the following drawing.",
        source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/p1_hmm.pdf",
        embedded_image_count=0,
        drawing_count=3,
        raster_fallback_needed=True,
    )

    records = extract_figure_records(
        manual=_manual(),
        pdf_path=Path("missing.pdf"),
        pages=[page],
        output_dir=Path("data/extracted/test_figures"),
        write_images=False,
    )

    assert len(records) == 1
    assert records[0].image_id == "thinkpad_p1_gen4_hmm_p072_raster"
    assert records[0].storage_uri is None
    assert records[0].citation.page_start == 72
    assert "thermal fan" in records[0].surrounding_text
