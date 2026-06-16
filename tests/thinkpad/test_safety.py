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


def test_bare_battery_prose_is_not_a_warning():
    """A page that merely mentions 'battery' or 'system board' in ordinary
    removal prose, with no DANGER/CAUTION/imperative trigger, must not emit a
    warning (AGENTS.md 6.6 — no false-positive safety records).
    """

    page = HMMPage(
        manual_id="thinkpad_e15_gen2_hmm",
        page=72,
        source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/e15_hmm.pdf",
        text=(
            "Removal steps of the built-in battery\n"
            "Disconnect the battery connector from the system board.\n"
            "Remove the four screws and lift the battery out.\n"
        ),
    )

    warnings = extract_warning_records(_manual(), [page])

    assert warnings == []


def test_caution_imperative_battery_is_a_warning():
    page = HMMPage(
        manual_id="thinkpad_e15_gen2_hmm",
        page=64,
        source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/e15_hmm.pdf",
        text=(
            "CAUTION: The battery could explode if handled incorrectly. "
            "Do not crush the battery."
        ),
    )

    warnings = extract_warning_records(_manual(), [page])

    assert any(w.warning_level == "CAUTION" for w in warnings)
    assert any(w.related_component == "battery" for w in warnings)
