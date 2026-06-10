from __future__ import annotations

from pathlib import Path

from src.thinkpad.manifest import load_manifest
from src.thinkpad.tool_service import ThinkPadToolService

GEN9_MANUAL = "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm"
GEN10_MANUAL = "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm"
SOURCE_URL = "https://download.lenovo.com/pccbbs/mobiles_pdf/tp_x1_carbon_gen9_x1_yoga_gen6_hmm_en.pdf"


def _manuals():
    return load_manifest(Path("tests/fixtures/thinkpad_mini_manifest.yaml"))


def _citation(page: int, section_id: str | None = None) -> dict:
    return {
        "manual_id": GEN9_MANUAL,
        "source_url": SOURCE_URL,
        "page_start": page,
        "page_end": page,
        "section": f"{section_id} Built-in battery" if section_id else None,
        "section_id": section_id,
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
                    "FRU or action": "Run setup and check the coin-cell battery.",
                },
                "citation": _citation(40),
            },
            {
                "record_id": "battery_screw",
                "manual_id": GEN9_MANUAL,
                "page": 72,
                "table_type": "screw_spec",
                "columns": ["Component", "Screw"],
                "row": {
                    "Component": "Built-in battery",
                    "Screw": "M2 x 3 mm",
                },
                "citation": _citation(72, "1050"),
            },
        ],
        fru_procedures=[
            {
                "procedure_id": "gen9_1050",
                "manual_id": GEN9_MANUAL,
                "fru_id": "1050",
                "fru_name": "Built-in battery",
                "steps": ["Disable the built-in battery.", "Remove the base cover.", "Remove the battery screws."],
                "prerequisites": ["1010"],
                "warnings": [],
                "related_image_ids": ["fig_battery"],
                "citation": _citation(70, "1050"),
            }
        ],
        figures=[
            {
                "image_id": "fig_battery",
                "manual_id": GEN9_MANUAL,
                "page": 71,
                "caption": "Built-in battery location",
                "surrounding_text": "Remove the built-in battery screws.",
                "related_component": "battery",
                "related_fru_id": "1050",
                "storage_uri": "data/images/fig_battery.png",
                "citation": _citation(71, "1050"),
            }
        ],
        warnings=[
            {
                "warning_id": "warn_battery",
                "manual_id": GEN9_MANUAL,
                "page": 7,
                "warning_level": "DANGER",
                "text": "Disconnect the battery before servicing the computer.",
                "related_component": "battery",
                "citation": _citation(7),
            }
        ],
    )


def test_list_supported_models_from_manifest() -> None:
    response = _service().list_supported_models()

    assert response["status"] == "ok"
    assert response["metadata"]["manual_count"] == 5
    assert any(GEN9_MANUAL == item["manual_id"] for item in response["results"])
    assert any("20XW" in item.get("machine_types", []) for item in response["results"])


def test_resolve_model_reports_ambiguity_and_machine_type_match() -> None:
    service = _service()

    ambiguous = service.resolve_thinkpad_model("X1 Carbon battery removal")
    assert ambiguous["status"] == "clarification_required"
    assert ambiguous["clarification_needed"] is True

    exact = service.resolve_thinkpad_model("21CB battery removal")
    assert exact["status"] == "ok"
    assert exact["results"][0]["manual_id"] == GEN10_MANUAL


def test_lookup_error_code_returns_structured_row_with_citation() -> None:
    response = _service().lookup_error_code("0271")

    assert response["status"] == "ok"
    assert response["results"][0]["table_type"] == "error_code"
    assert response["results"][0]["row"]["Symptom or error"].startswith("0271")
    assert response["citations"][0]["manual_id"] == GEN9_MANUAL
    assert response["citations"][0]["page_start"] == 40


def test_get_screw_spec_does_not_infer_missing_values() -> None:
    response = _service().get_screw_spec("X1 Carbon Gen 9", "battery")

    assert response["status"] == "ok"
    row = response["results"][0]["row"]
    assert row["Screw"] == "M2 x 3 mm"
    assert "Torque" not in row


def test_get_fru_procedure_requires_unambiguous_model() -> None:
    service = _service()

    ambiguous = service.get_fru_procedure("X1 Carbon", "battery")
    assert ambiguous["status"] == "clarification_required"
    assert ambiguous["results"] == []

    exact = service.get_fru_procedure("X1 Carbon Gen 9", "battery")
    assert exact["status"] == "ok"
    assert exact["results"][0]["fru_id"] == "1050"
    assert exact["results"][0]["prerequisites"] == ["1010"]


def test_related_diagram_returns_metadata_only() -> None:
    response = _service().get_related_diagram("X1 Carbon Gen 9", "battery", include_images=True)

    assert response["status"] == "ok"
    assert response["metadata"]["include_images_requested"] is True
    assert response["metadata"]["image_bytes_returned"] is False
    assert "image_bytes" not in response["results"][0]
    assert response["results"][0]["storage_uri"] == "data/images/fig_battery.png"


def test_safety_warnings_return_cited_records() -> None:
    response = _service().get_safety_warnings("X1 Carbon Gen 9", "battery")

    assert response["status"] == "ok"
    assert response["results"][0]["warning_level"] == "DANGER"
    assert response["citations"][0]["page_start"] == 7


def test_query_thinkpad_service_wraps_retrieval_evidence() -> None:
    class _RetrievalResponse:
        def to_dict(self):
            return {
                "query": "battery",
                "clarification_needed": False,
                "reason": None,
                "model_resolution": {},
                "results": [
                    {
                        "chunk_id": "fru::gen9_1050",
                        "score": 1.2,
                        "text": "Built-in battery",
                        "metadata": {"record_type": "fru_procedure"},
                        "citation": _citation(70, "1050"),
                    }
                ],
                "domain_rerank": [{"chunk_id": "fru::gen9_1050", "domain_score": 1.2}],
                "rerank_fallback": False,
            }

    def _fake_retriever(**kwargs):
        return _RetrievalResponse()

    service = ThinkPadToolService(manuals=_manuals(), retriever=_fake_retriever)
    response = service.query_thinkpad_service("X1 Carbon Gen 9 battery removal")

    assert response["status"] == "ok"
    assert response["results"][0]["chunk_id"] == "fru::gen9_1050"
    assert response["metadata"]["domain_rerank"][0]["chunk_id"] == "fru::gen9_1050"
