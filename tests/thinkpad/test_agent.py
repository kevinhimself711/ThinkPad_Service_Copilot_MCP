from __future__ import annotations

from typing import Any

from scripts.thinkpad_generate_agent_eval_candidates import _is_service_procedure_candidate
from src.libs.llm.base_llm import BaseLLM, ChatResponse, Message
from src.thinkpad.agent import plan_thinkpad_repair
from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.tool_service import ThinkPadToolService


class FakeLLM(BaseLLM):
    def __init__(self, content: str | list[str]) -> None:
        self.contents = [content] if isinstance(content, str) else list(content)
        self.calls = 0

    def chat(self, messages: list[Message], trace: Any | None = None, **kwargs: Any) -> ChatResponse:
        index = min(self.calls, len(self.contents) - 1)
        self.calls += 1
        return ChatResponse(content=self.contents[index], model="fake")


class FailingLLM(BaseLLM):
    def chat(self, messages: list[Message], trace: Any | None = None, **kwargs: Any) -> ChatResponse:
        raise RuntimeError("DashScope chat request failed: sk-test-secret should not leak")


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
    assert any(step.action == "Remove the built-in battery." for step in result.repair_plan)
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


def test_agent_unsupported_generation_is_not_ambiguous_clarification() -> None:
    service = ThinkPadToolService(manuals=[_manual_gen9(), _manual_gen10()])

    result = plan_thinkpad_repair("X1 Carbon Gen 11 battery removal plan", service)

    assert result.status == "not_found"
    assert result.clarification_needed is False
    assert result.refusal is not None
    assert result.refusal.reason == "unsupported_generation"
    assert [trace.tool for trace in result.tool_trace] == ["resolve_thinkpad_model"]


def test_agent_component_aliases_resolve_to_hmm_fru_names() -> None:
    service = _service_with_records()

    internal_battery = plan_thinkpad_repair("21CB internal battery removal plan", service)
    lower_cover = plan_thinkpad_repair("21CB lower cover removal plan", service)

    assert internal_battery.status == "ok"
    assert any(step.action == "Remove the built-in battery." for step in internal_battery.repair_plan)
    assert lower_cover.status == "ok"
    assert any(step.action == "Remove the base cover assembly." for step in lower_cover.repair_plan)


def test_agent_dependency_chain_phrasing_calls_graph_tool() -> None:
    service = _service_with_records()

    result = plan_thinkpad_repair("21CB built-in battery prerequisite chain", service)

    assert result.status == "ok"
    assert [trace.tool for trace in result.tool_trace] == [
        "resolve_thinkpad_model",
        "get_fru_dependency_chain",
    ]
    assert result.evidence_bundle.dependency_chain
    assert any(step.evidence_type == "fru_dependency_chain" for step in result.repair_plan)


def test_agent_fake_llm_unsupported_identifier_is_marked() -> None:
    service = _service_with_records()

    result = plan_thinkpad_repair(
        "21CB battery removal plan",
        service,
        use_llm=True,
        llm=FakeLLM(_llm_json("Replace unsupported FRU 9999.", extra_citations=True)),
    )

    assert result.status == "error"
    assert result.generated_answer is not None
    assert result.validation["unsupported_claim_count"] >= 1
    assert any("9999" in claim for claim in result.validation["unsupported_claims"])


def test_agent_fake_llm_repairs_uncited_first_response() -> None:
    service = _service_with_records()
    llm = FakeLLM(
        [
            "uncited prose plan",
            _llm_json("Use only the cited built-in battery evidence.", extra_citations=True),
        ]
    )

    result = plan_thinkpad_repair(
        "21CB battery removal plan",
        service,
        use_llm=True,
        llm=llm,
        llm_repair_attempts=1,
    )

    assert result.status == "ok"
    assert llm.calls == 2
    assert result.validation["llm_repair_attempted"] is True
    assert result.validation["llm_repair_succeeded"] is True
    assert result.validation["failure_reason"] is None


def test_agent_fake_llm_failed_repair_records_failure_reason() -> None:
    service = _service_with_records()
    bad = _llm_json("Replace unsupported FRU 9999.", extra_citations=True)

    result = plan_thinkpad_repair(
        "21CB battery removal plan",
        service,
        use_llm=True,
        llm=FakeLLM([bad, bad]),
        llm_repair_attempts=1,
    )

    assert result.status == "error"
    assert result.validation["llm_repair_attempted"] is True
    assert result.validation["llm_repair_succeeded"] is False
    assert result.validation["failure_reason"] == "unsupported_numeric_identifier"


def test_agent_provider_error_does_not_leak_secret() -> None:
    service = _service_with_records()

    result = plan_thinkpad_repair(
        "21CB battery removal plan",
        service,
        use_llm=True,
        llm=FailingLLM(),
        llm_repair_attempts=1,
    )

    serialized = result.to_json()
    assert result.status == "ok"
    assert result.validation["provider_error"] is True
    assert result.validation["provider_error_recovered"] is True
    assert result.validation["llm_repair_succeeded"] is True
    assert "sk-test-secret" not in serialized


def test_stress_generator_filters_diagnostic_pseudo_fru() -> None:
    assert _is_service_procedure_candidate({"fru_id": "1020", "fru_name": "Built-in battery"})
    assert not _is_service_procedure_candidate({"fru_id": "2204", "fru_name": "System configuration data is invalid"})
    assert not _is_service_procedure_candidate({"fru_id": "2201", "fru_name": "Machine UUID is invalid"})


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


def _llm_json(action: str, extra_citations: bool = False) -> str:
    manual = "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm"
    citations = [f"[{manual} p.72]"]
    if extra_citations:
        citations.append(f"[{manual} p.70]")
    return (
        "{"
        f"\"steps\":[{{\"title\":\"Use evidence\",\"action\":\"{action}\",\"citations\":[\"{citations[0]}\"]}}],"
        f"\"citations\":{citations!r},"
        "\"warnings\":[],"
        "\"limitations\":[]"
        "}"
    ).replace("'", '"')
