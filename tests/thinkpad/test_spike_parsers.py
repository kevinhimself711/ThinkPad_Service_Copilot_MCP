from src.thinkpad.spike import (
    classify_table_text,
    extract_prerequisites,
    find_fru_sections,
    find_safety_warnings,
)


def test_classify_table_text_identifies_core_hmm_table_types():
    assert classify_table_text("Error code Symptom Action\n0271 Date and time Run setup") == "error_code"
    assert classify_table_text("Screw Torque\nM2 x 3 mm 0.181 Nm") == "screw_spec"
    assert classify_table_text("FRU Part number Description") == "fru"


def test_find_fru_sections_preserves_prerequisite_references():
    text = """1010 Base cover assembly

Before removing the built-in battery, remove the following FRUs:
1010 Base cover assembly

1020 Built-in battery

Removal steps of the built-in battery.
"""

    sections = find_fru_sections(text, page=12)

    assert [section.fru_id for section in sections] == ["1010", "1020"]
    assert sections[0].page == 12
    assert "1010 Base cover assembly" in sections[0].prerequisites


def test_extract_prerequisites_deduplicates_fru_references():
    text = (
        "For access, remove these FRUs: 1010 Base cover assembly, "
        "1020 Built-in battery, and 1010 Base cover assembly."
    )

    assert extract_prerequisites(text) == [
        "1010 Base cover assembly",
        "1020 Built-in battery",
    ]


def test_find_safety_warnings_returns_page_level_markers_only():
    warnings = find_safety_warnings(
        "DANGER\nBefore replacing the battery, read the safety notice. CAUTION: ESD.",
        page=7,
    )

    assert {warning.warning_level for warning in warnings} >= {"DANGER", "CAUTION"}
    assert all(warning.page == 7 for warning in warnings)
