from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import HMMPage
from src.thinkpad.safety import extract_warning_records


def _manual() -> ManualMetadata:
    return ManualMetadata.from_mapping(
        {
            "manual_id": "thinkpad_e15_gen2_hmm",
            "title": "ThinkPad E15 Gen 2 Hardware Maintenance Manual",
            "models": ["ThinkPad E15 Gen 2"],
            "generations": ["Gen 2"],
            "machine_types": ["20TD"],
            "source_type": "lenovo_official",
            "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/e15_hmm.pdf",
            "local_pdf_path": "data/manuals/e15_hmm.pdf",
        }
    )


def test_extract_warning_records_emits_cited_safety_markers():
    page = HMMPage(
        manual_id="thinkpad_e15_gen2_hmm",
        page=10,
        source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/e15_hmm.pdf",
        text="DANGER: Before replacing the battery, observe ESD handling for the system board.",
    )

    warnings = extract_warning_records(_manual(), [page])

    levels = {warning.warning_level for warning in warnings}
    assert "DANGER" in levels
    assert "SAFETY_RELATED" in levels
    assert "CAUTION" in levels
    assert all(warning.citation.page_start == 10 for warning in warnings)


def test_extract_warning_records_ignores_toc_battery_mentions():
    page = HMMPage(
        manual_id="thinkpad_e15_gen2_hmm",
        page=3,
        source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/e15_hmm.pdf",
        text=(
            "Contents\n"
            "Chapter 1. Safety information . . . . . . 1\n"
            "Checking the built-in battery . . . . . . 51\n"
            "Checking the coin-cell battery . . . . . . 52\n"
            "Important notice for replacing a system board . . . . . . 20\n"
        ),
    )

    warnings = extract_warning_records(_manual(), [page])

    assert warnings == []
