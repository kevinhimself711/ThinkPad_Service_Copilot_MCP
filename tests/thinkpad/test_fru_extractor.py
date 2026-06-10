from src.thinkpad.fru_extractor import extract_fru_procedures
from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import HMMPage


def _manual() -> ManualMetadata:
    return ManualMetadata.from_mapping(
        {
            "manual_id": "thinkpad_x1_carbon_gen9_hmm",
            "title": "ThinkPad X1 Carbon Gen 9 Hardware Maintenance Manual",
            "models": ["ThinkPad X1 Carbon Gen 9"],
            "generations": ["Gen 9"],
            "machine_types": ["20XW"],
            "source_type": "lenovo_official",
            "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            "local_pdf_path": "data/manuals/x1_hmm.pdf",
        }
    )


def test_extract_fru_procedures_preserves_prerequisite_chain():
    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=67,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            text="""1010 Base cover assembly

Removal steps of the base cover assembly
Remove the screws.
Lift the base cover.

1050 Built-in battery

Before removing the built-in battery, remove the following FRUs:
1010 Base cover assembly

Removal steps of the built-in battery
Disconnect the battery connector.
Remove the battery.
""",
        )
    ]

    procedures, edges = extract_fru_procedures(_manual(), pages)

    assert [procedure.fru_id for procedure in procedures] == ["1010", "1050"]
    battery = [procedure for procedure in procedures if procedure.fru_id == "1050"][0]
    assert battery.prerequisites == ["1010 Base cover assembly"]
    assert battery.citation.section_id == "1050"
    assert battery.page_start == 67
    assert [(edge.source_fru_id, edge.required_fru_id) for edge in edges] == [("1050", "1010")]


def test_extract_fru_procedures_does_not_treat_error_code_as_fru_heading():
    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=42,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            text="""0271 Check Date and Time settings
Run the setup utility.

1010 Base cover assembly
Removal steps of the base cover assembly
Remove the screws.
""",
        )
    ]

    procedures, edges = extract_fru_procedures(_manual(), pages)

    assert [procedure.fru_id for procedure in procedures] == ["1010"]
    assert edges == []
