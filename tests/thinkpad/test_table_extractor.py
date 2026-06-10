from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import HMMPage
from src.thinkpad.table_extractor import extract_table_records


def _manual() -> ManualMetadata:
    return ManualMetadata.from_mapping(
        {
            "manual_id": "thinkpad_t14_gen2_p14s_gen2_hmm",
            "title": "ThinkPad T14 Gen 2 Hardware Maintenance Manual",
            "models": ["ThinkPad T14 Gen 2"],
            "generations": ["Gen 2"],
            "machine_types": ["20W1"],
            "source_type": "lenovo_official",
            "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/t14_gen2_p14s_gen2_hmm_en.pdf",
            "local_pdf_path": "data/manuals/t14_gen2_p14s_gen2_hmm_en.pdf",
        }
    )


def test_extract_table_records_preserves_row_column_alignment():
    page = HMMPage(
        manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
        page=68,
        text="1010 Base cover assembly\nScrew Torque table",
        source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/t14_gen2_p14s_gen2_hmm_en.pdf",
        table_blocks=[
            [
                ["Step", "Screw", "Torque"],
                ["1010", "M2 x 5 mm", "0.181 Nm"],
            ]
        ],
    )

    records = extract_table_records(_manual(), [page])

    assert len(records) == 1
    assert records[0].table_type == "screw_spec"
    assert records[0].columns == ["Step", "Screw", "Torque"]
    assert records[0].row == {"Step": "1010", "Screw": "M2 x 5 mm", "Torque": "0.181 Nm"}
    assert records[0].citation.page_start == 68
    assert records[0].parent_section == "1010 Base cover assembly"


def test_extract_table_records_handles_markdown_fixture_tables():
    page = HMMPage(
        manual_id="thinkpad_t14_gen2_p14s_gen2_hmm",
        page=42,
        text="""| Error code | Symptom | Action |
|---|---|---|
| 0271 | Check Date and Time settings | Run setup |
""",
        source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/t14_gen2_p14s_gen2_hmm_en.pdf",
    )

    records = extract_table_records(_manual(), [page])

    assert len(records) == 1
    assert records[0].table_type == "error_code"
    assert records[0].row["Error code"] == "0271"
    assert records[0].row["Action"] == "Run setup"
