from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.mcp_server.protocol_handler import ProtocolHandler, _register_default_tools
from src.mcp_server.tools import thinkpad_tools
from src.thinkpad.manifest import load_manifest
from src.thinkpad.tool_service import ThinkPadToolService

GEN9_MANUAL = "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm"


def _manuals():
    return load_manifest(Path("tests/fixtures/thinkpad_mini_manifest.yaml"))


def _citation() -> dict:
    return {
        "manual_id": GEN9_MANUAL,
        "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/tp_x1_carbon_gen9_x1_yoga_gen6_hmm_en.pdf",
        "page_start": 40,
        "page_end": 40,
        "section": None,
        "section_id": None,
    }


def _service() -> ThinkPadToolService:
    return ThinkPadToolService(
        manuals=_manuals(),
        tables=[
            {
                "record_id": "error_0271",
                "manual_id": GEN9_MANUAL,
                "page": 40,
                "table_type": "error_code",
                "columns": ["Symptom or error", "FRU or action"],
                "row": {
                    "Symptom or error": "0271 Date and time error",
                    "FRU or action": "Run setup.",
                },
                "citation": _citation(),
            }
        ],
        fru_procedures=[
            {
                "procedure_id": "gen9_1010",
                "manual_id": GEN9_MANUAL,
                "fru_id": "1010",
                "fru_name": "Base cover assembly",
                "steps": ["Remove the base cover."],
                "prerequisites": [],
                "warnings": [],
                "related_image_ids": [],
                "citation": {**_citation(), "section_id": "1010"},
            },
            {
                "procedure_id": "gen9_1050",
                "manual_id": GEN9_MANUAL,
                "fru_id": "1050",
                "fru_name": "Built-in battery",
                "steps": ["Remove the battery."],
                "prerequisites": ["1010"],
                "warnings": [],
                "related_image_ids": [],
                "citation": {**_citation(), "section_id": "1050"},
            },
        ],
        dependency_edges=[
            {
                "manual_id": GEN9_MANUAL,
                "source_fru_id": "1050",
                "required_fru_id": "1010",
                "citation": {**_citation(), "section_id": "1050"},
            }
        ],
    )


def _json_from_call_result(result) -> dict:
    assert result.content
    assert result.content[0].type == "text"
    return json.loads(result.content[0].text)


def test_register_thinkpad_tools_declares_expected_schemas() -> None:
    protocol = ProtocolHandler(server_name="test", server_version="0")

    thinkpad_tools.register_tools(protocol)

    expected = {
        "list_supported_models",
        "resolve_thinkpad_model",
        "query_thinkpad_service",
        "lookup_error_code",
        "get_fru_procedure",
        "get_fru_dependency_chain",
        "get_screw_spec",
        "get_related_diagram",
        "get_safety_warnings",
    }
    assert expected.issubset(protocol.tools.keys())
    for name in expected:
        schema = protocol.tools[name].input_schema
        assert schema["type"] == "object"
        assert "properties" in schema


def test_default_protocol_registration_includes_thinkpad_tools() -> None:
    protocol = ProtocolHandler(server_name="test", server_version="0")

    _register_default_tools(protocol)

    assert "query_knowledge_hub" in protocol.tools
    assert "lookup_error_code" in protocol.tools
    assert "get_fru_dependency_chain" in protocol.tools
    assert "get_safety_warnings" in protocol.tools


def test_handler_returns_json_call_tool_result() -> None:
    thinkpad_tools.set_tool_service_for_testing(_service())
    try:
        result = asyncio.run(thinkpad_tools.lookup_error_code_handler(error_code="0271"))
    finally:
        thinkpad_tools.set_tool_service_for_testing(None)

    assert result.isError is False
    payload = _json_from_call_result(result)
    assert payload["tool"] == "lookup_error_code"
    assert payload["status"] == "ok"
    assert payload["results"][0]["row"]["Symptom or error"].startswith("0271")
    assert payload["citations"][0]["manual_id"] == GEN9_MANUAL


def test_dependency_chain_handler_returns_graph_evidence() -> None:
    thinkpad_tools.set_tool_service_for_testing(_service())
    try:
        result = asyncio.run(
            thinkpad_tools.get_fru_dependency_chain_handler(
                model="X1 Carbon Gen 9",
                component_or_fru="battery",
            )
        )
    finally:
        thinkpad_tools.set_tool_service_for_testing(None)

    assert result.isError is False
    payload = _json_from_call_result(result)
    assert payload["tool"] == "get_fru_dependency_chain"
    assert payload["status"] == "ok"
    assert payload["results"][0]["record_type"] == "fru_dependency_chain"
    assert payload["results"][0]["dependency_chain"][0]["fru_id"] == "1010"


def test_protocol_invalid_params_returns_error_without_traceback() -> None:
    protocol = ProtocolHandler(server_name="test", server_version="0")
    thinkpad_tools.register_tools(protocol)

    result = asyncio.run(protocol.execute_tool("lookup_error_code", {}))

    assert result.isError is True
    text = result.content[0].text
    assert "Invalid parameters" in text
    assert "Traceback" not in text


def test_resolve_handler_reports_ambiguity_as_non_error_json() -> None:
    thinkpad_tools.set_tool_service_for_testing(_service())
    try:
        result = asyncio.run(thinkpad_tools.resolve_thinkpad_model_handler("X1 Carbon battery removal"))
    finally:
        thinkpad_tools.set_tool_service_for_testing(None)

    assert result.isError is False
    payload = _json_from_call_result(result)
    assert payload["status"] == "clarification_required"
    assert payload["clarification_needed"] is True
