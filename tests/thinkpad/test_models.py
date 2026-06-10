import json

import pytest

from src.thinkpad.models import (
    Citation,
    DependencyEdge,
    DomainModelError,
    FigureRecord,
    FRUProcedure,
    TableRecord,
    WarningRecord,
)


def _citation() -> Citation:
    return Citation(
        manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
        source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/t14_gen2_p14s_gen2_hmm_en.pdf",
        page_start=68,
        section="1010 Base cover assembly",
        section_id="1010",
    )


def test_citation_serializes_to_json_safe_dict():
    citation = _citation()

    assert citation.to_dict()["manual_id"] == "thinkpad_t14_gen2_p14s_gen2_hmm"
    json.dumps(citation.to_dict())


def test_citation_rejects_missing_required_grounding_fields():
    with pytest.raises(DomainModelError, match="manual_id"):
        Citation(manual_id="", source_url="https://download.lenovo.com/manual.pdf", page_start=1)

    with pytest.raises(DomainModelError, match="page_start"):
        Citation(manual_id="manual", source_url="https://download.lenovo.com/manual.pdf", page_start=0)


def test_table_record_preserves_structured_row_and_citation():
    record = TableRecord(
        record_id="table-001-row-001",
        manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
        page=68,
        table_type="screw_spec",
        columns=["Step", "Screw", "Torque"],
        row={"Step": "1010", "Screw": "M2 x 5 mm", "Torque": "0.181 Nm"},
        citation=_citation(),
        parent_section="1010 Base cover assembly",
    )

    payload = record.to_dict()

    assert payload["row"]["Torque"] == "0.181 Nm"
    assert payload["citation"]["page_start"] == 68
    json.dumps(payload)


def test_record_rejects_citation_manual_mismatch():
    citation = Citation(
        manual_id="other_manual",
        source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/manual.pdf",
        page_start=1,
    )

    with pytest.raises(DomainModelError, match="citation.manual_id"):
        TableRecord(
            record_id="row-1",
            manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
            page=1,
            table_type="fru",
            columns=["FRU", "Name"],
            row={"FRU": "1010", "Name": "Base cover assembly"},
            citation=citation,
        )


def test_figure_warning_procedure_and_dependency_records_serialize():
    warning = WarningRecord(
        warning_id="warn-001",
        manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
        warning_level="DANGER",
        text="Disconnect battery before servicing.",
        citation=_citation(),
        page=68,
        related_component="battery",
    )
    figure = FigureRecord(
        image_id="fig-001",
        manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
        page=68,
        citation=_citation(),
        caption="Base cover screw layout",
        bbox=(1.0, 2.0, 3.0, 4.0),
    )
    procedure = FRUProcedure(
        procedure_id="fru-1010",
        manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
        fru_id="1010",
        fru_name="Base cover assembly",
        citation=_citation(),
        steps=["Remove screws.", "Lift the base cover."],
        prerequisites=[],
        warnings=[warning],
        related_image_ids=[figure.image_id],
        page_start=68,
        page_end=69,
    )
    edge = DependencyEdge(
        manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
        source_fru_id="1050",
        required_fru_id="1010",
        citation=_citation(),
    )

    assert procedure.to_dict()["warnings"][0]["warning_level"] == "DANGER"
    assert edge.to_dict()["relation_type"] == "FRU_REQUIRES_PREREQUISITE_FRU"
    json.dumps(figure.to_dict())
