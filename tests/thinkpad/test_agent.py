from __future__ import annotations

from typing import Any

from src.libs.llm.base_llm import BaseLLM, ChatResponse, Message
from src.thinkpad.agent import plan_thinkpad_repair
from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.tool_service import ThinkPadToolService


class FakeLLM(BaseLLM):
    def __init__(self, content: str) -> None:
        self.content = content

    def chat(self, messages: list[Message], trace: Any | None = None, **kwargs: Any) -> ChatResponse:
        return ChatResponse(content=self.content, model="fake")


def test_agent_ambiguous_model_returns_clarification() -> None:
    service = ThinkPadToolService(manuals=[_manual_gen9(), _manual_gen10()])

    result = plan_thinkpad_repair("X1 Carbon battery removal plan", service)

    assert result.status == "clarification_required"
    assert result.clarification_needed is True
    assert [trace.tool for trace in result.tool_trace] == ["resolve_thinkpad_model"]
    assert not result.repair_plan


def test_agent_machine_type_plan_calls_expected_tools_and_cites() -> None:
    service = _service_with_records()

    result = plan_thinkpad_repair("21CB battery removal plan", service)

    assert result.status == "ok"
    assert [trace.tool for trace in result.tool_trace] == [
        "resolve_thinkpad_model",
        "get_fru_procedure",
        "get_fru_dependency_chain",
        "get_related_diagram",
        "get_safety_warnings",
    ]
    assert all("get_screw_spec" != trace.tool for trace in result.tool_trace)
    assert result.repair_plan
    assert result.citations
    assert result.validation["minimum_citations_present"] is True


def test_agent_screw_query_uses_screw_lookup_without_procedure_tools() -> None:
    service = _service_with_records()

    result = plan_thinkpad_repair("21CB screw spec M2 x 3", service)

    tools = [trace.tool for trace in result.tool_trace]
    assert result.status == "ok"
    assert "get_screw_spec" in tools
    assert "get_fru_procedure" not in tools
    assert result.evidence_bundle.screw_specs


def test_agent_unsupported_model_does_not_call_llm() -> None:
    service = _service_with_records()

    result = plan_thinkpad_repair(
        "IdeaPad 5 battery removal plan",
        service,
        use_llm=True,
        llm=FakeLLM("should not be used"),
    )

    assert result.status == "not_found"
    assert result.generated_answer is None
    assert [trace.tool for trace in result.tool_trace] == ["resolve_thinkpad_model"]


def test_agent_fake_llm_unsupported_identifier_is_marked() -> None:
    service = _service_with_records()

    result = plan_thinkpad_repair(
        "21CB battery removal plan",
        service,
        use_llm=True,
        llm=FakeLLM("Replace unsupported FRU 9999."),
    )

    assert result.status == "ok"
    assert result.generated_answer is not None
    assert result.validation["unsupported_claim_count"] >= 1
    assert any("9999" in claim for claim in result.validation["unsupported_claims"])


def _service_with_records() -> ThinkPadToolService:
    manual = _manual_gen10()
    citation_1010 = _citation("thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm", 70, "1010")
    citation_1020 = _citation("thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm", 72, "1020")
    procedures = [
        {
            "procedure_id": "p1010",
            "manual_id": manual.manual_id,
            "fru_id": "1010",
            "fru_name": "Base cover assembly",
            "citation": citation_1010,
            "page_start": 70,
            "page_end": 71,
            "steps": ["Remove the base cover assembly."],
            "prerequisites": [],
        },
        {
            "procedure_id": "p1020",
            "manual_id": manual.manual_id,
            "fru_id": "1020",
            "fru_name": "Built-in battery",
            "citation": citation_1020,
            "page_start": 72,
            "page_end": 73,
            "steps": ["Remove the built-in battery."],
            "prerequisites": ["1010 Base cover assembly"],
        },
    ]
    return ThinkPadToolService(
        manuals=[manual],
        tables=[
            {
                "record_id": "screw_1",
                "manual_id": manual.manual_id,
                "table_type": "screw_spec",
                "columns": ["Screw (quantity)", "Torque"],
                "row": {"Screw (quantity)": "M2 x 3 mm (1)", "Torque": "0.18 Nm"},
                "page": 72,
                "citation": _citation(manual.manual_id, 72, None),
            }
        ],
        fru_procedures=procedures,
        dependency_edges=[
            {
                "manual_id": manual.manual_id,
                "source_fru_id": "1020",
                "required_fru_id": "1010",
                "citation": citation_1020,
            }
        ],
        figures=[
            {
                "image_id": "figure_battery",
                "manual_id": manual.manual_id,
                "page": 72,
                "caption": "Battery diagram",
                "surrounding_text": "Built-in battery",
                "citation": _citation(manual.manual_id, 72, None),
            }
        ],
        warnings=[
            {
                "warning_id": "warning_battery",
                "manual_id": manual.manual_id,
                "page": 72,
                "warning_level": "CAUTION",
                "text": "Battery safety warning.",
                "related_component": "battery",
                "citation": _citation(manual.manual_id, 72, None),
            }
        ],
    )


def _manual_gen9() -> ManualMetadata:
    return ManualMetadata(
        manual_id="thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
        title="ThinkPad X1 Carbon Gen 9 HMM",
        models=["ThinkPad X1 Carbon Gen 9"],
        generations=["Gen 9"],
        machine_types=["20XW"],
        source_type="lenovo_official",
        source_url="https://download.lenovo.com/test/x1_gen9.pdf",
        local_pdf_path="data/manuals/x1_gen9.pdf",
    )


def _manual_gen10() -> ManualMetadata:
    return ManualMetadata(
        manual_id="thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
        title="ThinkPad X1 Carbon Gen 10 HMM",
        models=["ThinkPad X1 Carbon Gen 10"],
        generations=["Gen 10"],
        machine_types=["21CB"],
        source_type="lenovo_official",
        source_url="https://download.lenovo.com/test/x1_gen10.pdf",
        local_pdf_path="data/manuals/x1_gen10.pdf",
    )


def _citation(manual_id: str, page: int, section_id: str | None) -> dict[str, Any]:
    return {
        "manual_id": manual_id,
        "source_url": "https://download.lenovo.com/test/source.pdf",
        "page_start": page,
        "page_end": page,
        "section": None,
        "section_id": section_id,
    }
