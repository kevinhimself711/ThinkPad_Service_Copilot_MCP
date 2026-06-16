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


def test_extract_fru_procedures_adds_step_level_citations_across_pages():
    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=70,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            text="""1050 Built-in battery

Removal steps of the built-in battery
Disconnect the battery connector.
""",
        ),
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=71,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            text="""Remove the battery.
When installing: Attach the connector firmly.
""",
        ),
    ]

    procedures, _ = extract_fru_procedures(_manual(), pages)

    battery = procedures[0]
    assert battery.page_start == 70
    assert battery.page_end == 71
    assert [step.text for step in battery.step_records[:2]] == [
        "Disconnect the battery connector",
        "Remove the battery",
    ]
    assert [step.citation.page_start for step in battery.step_records[:2]] == [70, 71]
    assert [step.citation.section_id for step in battery.step_records[:2]] == ["1050", "1050"]


def test_extract_step_records_merges_wrapped_lines_and_drops_noise():
    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=72,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            text="""1010 Base cover assembly

Removal steps of the base cover assembly
Remove the five screws that secure the base cover
assembly to the bottom of the computer.
Lift the base cover assembly away from the
chassis as shown in the following illustration.
72
a
pcsupport.lenovo.com
When installing: Ensure that all the latches are
engaged before tightening the screws.
""",
        )
    ]

    procedures, _ = extract_fru_procedures(_manual(), pages)

    base = procedures[0]
    texts = [step.text for step in base.step_records]
    assert texts == [
        "Remove the five screws that secure the base cover assembly to the bottom of the computer",
        "Lift the base cover assembly away from the chassis as shown in the following illustration",
        "When installing: Ensure that all the latches are engaged before tightening the screws",
    ]
    assert all(step.citation.page_start == 72 for step in base.step_records)
    kinds = [step.step_kind for step in base.step_records]
    assert kinds == ["removal_step", "removal_step", "install_note"]


def test_image_only_removal_yields_no_removal_step():
    """A removal procedure that is an exploded-view image with only a When
    installing block must not produce removal_step records (AGENTS.md 6.4).
    """

    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=78,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            drawing_count=200,
            text="""1070 Thermal fan assembly

Removal steps of the thermal fan assembly
2c
2b
2a
2d
When installing:
Ensure that the connector is attached firmly.
Before you attach the fan assembly to the computer, apply thermal grease.
""",
        )
    ]

    procedures, _ = extract_fru_procedures(_manual(), pages)

    fan = procedures[0]
    removal = [s for s in fan.step_records if s.step_kind == "removal_step"]
    assert removal == []
    assert any(s.step_kind == "install_note" for s in fan.step_records)
    assert fan.presentation_type == "image_only"


def test_interleaved_presentation_with_figure_and_text_steps():
    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=82,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            drawing_count=300,
            text="""1090 Keyboard

Removal steps of the keyboard
Loosen the two screws that secure the keyboard.
Turn the computer over and open the display. Push hard to release the keyboard.
Pivot the keyboard slightly upward until you can see the connectors.
""",
        )
    ]

    procedures, _ = extract_fru_procedures(_manual(), pages)
    keyboard = procedures[0]
    removal = [s for s in keyboard.step_records if s.step_kind == "removal_step"]
    assert len(removal) >= 2
    assert keyboard.presentation_type == "interleaved"


def test_cross_reference_presentation_yields_no_steps():
    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=77,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            drawing_count=2,
            text="""1080 Thermal fan assembly (for AMD models)

Removal steps of the thermal fan assembly (for AMD models)
The removal steps are similar to that of Intel models.
""",
        )
    ]

    procedures, _ = extract_fru_procedures(_manual(), pages)
    fan = procedures[0]
    removal = [s for s in fan.step_records if s.step_kind == "removal_step"]
    assert removal == []
    assert fan.presentation_type == "cross_ref"


def test_software_calibration_steps_are_not_removal_steps():
    """X-Rite color-calibration / BIOS numbered steps inside an image-only
    section must not be misclassified as physical removal steps.
    """

    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=77,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            drawing_count=300,
            text="""1030 M.2 solid-state drive

Removal steps of the M.2 solid-state drive
1. Make sure the computer is connected to the Internet.
2. Open the pre-installed X-Rite Color Assistant app.
3. Go to Settings and restore profiles.
""",
        )
    ]

    procedures, _ = extract_fru_procedures(_manual(), pages)
    ssd = procedures[0]
    removal = [s for s in ssd.step_records if s.step_kind == "removal_step"]
    assert removal == []
    assert ssd.presentation_type == "image_only"


def test_variant_subprocedures_split_into_separate_procedures():
    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=83,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            drawing_count=300,
            text="""1100 Thermal fan assembly

Before removing the thermal fan assembly, remove these FRUs:
"1010 Base cover assembly"

Removal steps of the thermal fan assembly (for Intel models)
2e
When installing: Ensure that the connector is attached firmly.

Removal steps of the thermal fan assembly (for AMD models)
2a
When installing: Ensure that the connector is attached firmly.
""",
        )
    ]

    procedures, _ = extract_fru_procedures(_manual(), pages)
    fan = [p for p in procedures if p.fru_id == "1100"]
    assert len(fan) == 2
    ids = sorted(p.procedure_id for p in fan)
    assert ids[0].endswith("_amd_models")
    assert ids[1].endswith("_intel_models")


def test_non_variant_section_is_not_split():
    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=72,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            drawing_count=300,
            text="""1010 Base cover assembly

Removal steps of the base cover assembly
Remove the screws.
Lift the base cover assembly.
""",
        )
    ]

    procedures, _ = extract_fru_procedures(_manual(), pages)
    base = [p for p in procedures if p.fru_id == "1010"]
    assert len(base) == 1
    assert base[0].procedure_id.endswith("_fru_1010")


def test_interleaved_steps_across_pages_are_not_dropped():
    """A removal step that begins a new page after a figure (e.g. the keyboard
    "Put the keyboard on the palm rest...") must not be dropped or merged into
    the previous step. Regression for the T480 keyboard interleaved case.
    """

    pages = [
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=81,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            drawing_count=300,
            text="""1090 Keyboard

Removal steps of the keyboard
Loosen the two screws that secure the keyboard.
""",
        ),
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=82,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            drawing_count=300,
            text="""Turn the computer over and open the display. Push hard to release the keyboard.
Pivot the keyboard slightly upward until you can see the connectors.
""",
        ),
        HMMPage(
            manual_id="thinkpad_x1_carbon_gen9_hmm",
            page=83,
            source_url="https://download.lenovo.com/pccbbs/mobiles_pdf/x1_hmm.pdf",
            drawing_count=300,
            text="""Put the keyboard on the palm rest and detach the connectors. Then remove the keyboard.
1100 Coin-cell battery
""",
        ),
    ]

    procedures, _ = extract_fru_procedures(_manual(), pages)
    keyboard = [p for p in procedures if p.fru_id == "1090"][0]
    removal = [s for s in keyboard.step_records if s.step_kind == "removal_step"]
    assert len(removal) == 4
    assert removal[3].text.startswith("Put the keyboard on the palm rest")
    assert removal[3].citation.page_start == 83
    assert keyboard.presentation_type == "interleaved"
