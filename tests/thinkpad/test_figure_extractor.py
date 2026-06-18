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
    # Legacy fallback (no `pages` passed): page-span containment, narrowest wins.
    assert by_id["img_p074"].related_fru_id == "1070"
    # page 99 belongs to no procedure span
    assert by_id["img_p099"].related_fru_id is None

    procs_by_id = {p.procedure_id: p for p in updated_procs}
    assert procs_by_id["thinkpad_p1_gen4_hmm_fru_1060"].related_image_ids == ["img_p072"]
    assert procs_by_id["thinkpad_p1_gen4_hmm_fru_1070"].related_image_ids == ["img_p074"]


def _proc(fru_id, name, page_start, page_end):
    from src.thinkpad.models import Citation, FRUProcedure

    return FRUProcedure(
        procedure_id=f"m_fru_{fru_id}",
        manual_id="m",
        fru_id=fru_id,
        fru_name=name,
        citation=Citation(manual_id="m", source_url="https://download.lenovo.com/x.pdf", page_start=page_start),
        page_start=page_start,
        page_end=page_end,
        presentation_type="image_only",
    )


def _raster(page):
    from src.thinkpad.models import Citation, FigureRecord

    return FigureRecord(
        image_id=f"m_p{page:03d}_raster",
        manual_id="m",
        page=page,
        citation=Citation(manual_id="m", source_url="https://download.lenovo.com/x.pdf", page_start=page),
        figure_kind="page_raster",
    )


def _page(page, headings, drawing_bands, drawing_rects=None):
    from src.thinkpad.models import HMMPage

    return HMMPage(
        manual_id="m",
        page=page,
        text="",
        source_url="https://download.lenovo.com/x.pdf",
        width=600.0,
        height=800.0,
        fru_headings=headings,
        drawing_bands=drawing_bands,
        drawing_rects=drawing_rects or [],
    )


def test_yband_raster_attribution_resolves_page_bleed():
    """A whole-page raster on a page shared by a bled span and the next FRU's
    heading goes to the FRU whose heading band owns the page's drawings
    (mirrors the real 1090/1100 bleed)."""
    from src.thinkpad.fru_extractor import attribute_figures_to_procedures

    procedures = [_proc("1090", "Built-in battery", 82, 83), _proc("1100", "Thermal fan assembly", 83, 84)]
    # page 83: 1100 heading at y=341; drawings mostly below it -> page belongs to 1100.
    pages = [
        _page(82, [(98.0, "1090")], [(120.0, 580.0)]),
        _page(83, [(341.0, "1100")], [(360.0, 585.0)]),
    ]
    figures = [_raster(82), _raster(83)]

    figs, _ = attribute_figures_to_procedures(figures, procedures, pages)
    by_id = {f.image_id: f.related_fru_id for f in figs}
    assert by_id["m_p082_raster"] == "1090"
    assert by_id["m_p083_raster"] == "1100"


def test_yband_multipage_diagram_not_stolen_by_next_fru():
    """A continued diagram page whose only heading is the NEXT FRU near the page
    bottom stays with the continuing FRU (mirrors 1010 spanning p72-74 where
    1020's heading is at the bottom of p74)."""
    from src.thinkpad.fru_extractor import attribute_figures_to_procedures

    procedures = [_proc("1010", "Keyboard", 72, 74), _proc("1020", "Base cover assembly", 74, 76)]
    pages = [
        _page(73, [], [(60.0, 700.0)]),  # no heading: continues 1010
        _page(74, [(693.0, "1020")], [(60.0, 690.0)]),  # drawings above 1020's bottom heading -> 1010
    ]
    figures = [_raster(73), _raster(74)]

    figs, _ = attribute_figures_to_procedures(figures, procedures, pages)
    by_id = {f.image_id: f.related_fru_id for f in figs}
    assert by_id["m_p073_raster"] == "1010"
    assert by_id["m_p074_raster"] == "1010"


def test_yband_embedded_image_uses_bbox_band():
    """An embedded image is attributed by which heading band its bbox falls in."""
    from src.thinkpad.fru_extractor import attribute_figures_to_procedures
    from src.thinkpad.models import Citation, FigureRecord

    procedures = [_proc("1060", "WWAN card", 79, 79), _proc("1070", "WLAN card", 79, 80)]
    pages = [_page(79, [(100.0, "1060"), (400.0, "1070")], [])]
    fig = FigureRecord(
        image_id="m_p079_img01",
        manual_id="m",
        page=79,
        citation=Citation(manual_id="m", source_url="https://download.lenovo.com/x.pdf", page_start=79),
        bbox=(50.0, 450.0, 300.0, 600.0),  # y-center 525 -> below 1070's heading
    )

    figs, _ = attribute_figures_to_procedures([fig], procedures, pages)
    assert figs[0].related_fru_id == "1070"


def test_yband_continuation_page_prefers_containing_span_over_narrowest():
    """Two FRUs share a page_start; the heading-less continuation pages belong to
    the one whose span CONTAINS them, not the narrowest (mirrors real P1 1080 vs
    1090: both start p79, but 1090 spans p79-82 and owns the p80-82 diagrams)."""
    from src.thinkpad.fru_extractor import attribute_figures_to_procedures

    procedures = [_proc("1080", "Coin-cell battery", 79, 79), _proc("1090", "M.2 solid-state drive", 79, 82)]
    pages = [
        _page(80, [], [(278.0, 300.0)]),  # no heading: continuation of 1090
        _page(81, [], [(332.0, 380.0)]),
        _page(82, [(579.0, "1100")], [(64.0, 535.0)]),  # 1100 heading low; drawings above -> continues 1090
    ]
    figures = [_raster(80), _raster(81), _raster(82)]

    figs, _ = attribute_figures_to_procedures(figures, procedures, pages)
    by_id = {f.image_id: f.related_fru_id for f in figs}
    assert by_id["m_p080_raster"] == "1090"
    assert by_id["m_p081_raster"] == "1090"
    assert by_id["m_p082_raster"] == "1090"


def test_region_crops_created_for_shared_raster_page_without_displacing_native_image():
    from src.thinkpad.fru_extractor import attribute_figures_to_procedures

    procedures = [_proc("1060", "WWAN card", 79, 79), _proc("1070", "WLAN card", 79, 79)]
    pages = [_page(79, [(100.0, "1060"), (410.0, "1070")], [(130.0, 270.0), (450.0, 620.0)])]
    figures = [_raster(79)]

    updated_figs, updated_procs = attribute_figures_to_procedures(figures, procedures, pages)

    regions = {f.related_fru_id: f for f in updated_figs if f.figure_kind == "region_crop"}
    assert set(regions) == {"1060", "1070"}
    assert regions["1060"].bbox == (0.0, 118.0, 600.0, 282.0)
    assert regions["1070"].bbox == (0.0, 438.0, 600.0, 632.0)
    assert regions["1060"].source_image_id == "m_p079_raster"

    procs = {p.fru_id: p for p in updated_procs}
    assert any(image_id.endswith("_region_1060") for image_id in procs["1060"].related_image_ids)
    assert any(image_id.endswith("_region_1070") for image_id in procs["1070"].related_image_ids)
    assert procs["1070"].related_image_ids[0] == "m_p079_raster"


def test_region_crop_uses_drawing_rects_for_narrow_bbox():
    from src.thinkpad.fru_extractor import attribute_figures_to_procedures

    procedures = [_proc("1060", "I/O bracket", 79, 79), _proc("1070", "WLAN card", 79, 79)]
    pages = [
        _page(
            79,
            [(100.0, "1060"), (410.0, "1070")],
            [(130.0, 270.0), (450.0, 620.0)],
            drawing_rects=[(40.0, 130.0, 180.0, 260.0), (360.0, 450.0, 520.0, 620.0)],
        )
    ]
    figures = [_raster(79)]

    updated_figs, _ = attribute_figures_to_procedures(figures, procedures, pages)

    wide_regions = {f.related_fru_id: f for f in updated_figs if f.figure_kind == "region_crop"}
    precise_regions = {f.related_fru_id: f for f in updated_figs if f.figure_kind == "region_crop_precise"}

    assert wide_regions["1060"].bbox == (0.0, 118.0, 600.0, 282.0)
    assert wide_regions["1070"].bbox == (0.0, 438.0, 600.0, 632.0)
    assert precise_regions["1060"].bbox == (40.0, 118.0, 180.0, 272.0)
    assert precise_regions["1070"].bbox == (360.0, 438.0, 520.0, 632.0)


def test_region_crop_above_first_heading_continues_preceding_fru():
    from src.thinkpad.fru_extractor import attribute_figures_to_procedures

    procedures = [_proc("1010", "Base cover", 72, 74), _proc("1020", "Battery", 74, 75)]
    pages = [_page(74, [(700.0, "1020")], [(60.0, 650.0)])]
    figures = [_raster(74)]

    updated_figs, updated_procs = attribute_figures_to_procedures(figures, procedures, pages)

    regions = [f for f in updated_figs if f.figure_kind == "region_crop"]
    assert len(regions) == 1
    assert regions[0].related_fru_id == "1010"
    procs = {p.fru_id: p for p in updated_procs}
    assert any(image_id.endswith("_region_1010") for image_id in procs["1010"].related_image_ids)
    assert procs["1010"].related_image_ids[0] == "m_p074_raster"


def test_region_crop_skips_diagnostic_pseudo_fru_ids():
    from src.thinkpad.fru_extractor import attribute_figures_to_procedures

    procedures = [
        _proc("2201", "Machine UUID is invalid", 40, 44),
        _proc("1060", "Thermal fan assembly", 44, 45),
    ]
    pages = [_page(44, [(100.0, "2201"), (400.0, "1060")], [(130.0, 250.0), (430.0, 560.0)])]
    figures = [_raster(44)]

    updated_figs, _ = attribute_figures_to_procedures(figures, procedures, pages)

    regions = {f.related_fru_id: f for f in updated_figs if f.figure_kind == "region_crop"}
    assert "2201" not in regions
    assert "1060" in regions
