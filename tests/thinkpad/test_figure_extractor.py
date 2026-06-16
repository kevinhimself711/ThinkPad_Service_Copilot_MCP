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


def test_attribute_figures_to_procedures_maps_by_page_span():
    from src.thinkpad.fru_extractor import attribute_figures_to_procedures
    from src.thinkpad.models import Citation, FigureRecord, FRUProcedure

    def _citation(page: int) -> Citation:
        return Citation(
            manual_id="thinkpad_p1_gen4_hmm",
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/p1_hmm.pdf",
            page_start=page,
        )

    procedures = [
        FRUProcedure(
            procedure_id="thinkpad_p1_gen4_hmm_fru_1060",
            manual_id="thinkpad_p1_gen4_hmm",
            fru_id="1060",
            fru_name="Thermal fan assembly",
            citation=_citation(72),
            page_start=72,
            page_end=74,
            presentation_type="image_only",
        ),
        FRUProcedure(
            procedure_id="thinkpad_p1_gen4_hmm_fru_1070",
            manual_id="thinkpad_p1_gen4_hmm",
            fru_id="1070",
            fru_name="Audio board",
            citation=_citation(74),
            page_start=74,
            page_end=74,
            presentation_type="image_only",
        ),
    ]
    figures = [
        FigureRecord(image_id="img_p072", manual_id="thinkpad_p1_gen4_hmm", page=72, citation=_citation(72)),
        FigureRecord(image_id="img_p074", manual_id="thinkpad_p1_gen4_hmm", page=74, citation=_citation(74)),
        FigureRecord(image_id="img_p099", manual_id="thinkpad_p1_gen4_hmm", page=99, citation=_citation(99)),
    ]

    updated_figs, updated_procs = attribute_figures_to_procedures(figures, procedures)

    by_id = {f.image_id: f for f in updated_figs}
    assert by_id["img_p072"].related_fru_id == "1060"
    # page 74 is in both spans; the narrowest (1070, width 0) wins
    assert by_id["img_p074"].related_fru_id == "1070"
    # page 99 belongs to no procedure span
    assert by_id["img_p099"].related_fru_id is None

    procs_by_id = {p.procedure_id: p for p in updated_procs}
    assert procs_by_id["thinkpad_p1_gen4_hmm_fru_1060"].related_image_ids == ["img_p072"]
    assert procs_by_id["thinkpad_p1_gen4_hmm_fru_1070"].related_image_ids == ["img_p074"]
