from __future__ import annotations

from pathlib import Path

from src.core.types import RetrievalResult
from src.thinkpad.domain_reranker import rerank_thinkpad_results
from src.thinkpad.manifest import load_manifest
from src.thinkpad.model_resolver import resolve_thinkpad_model


def _manuals():
    return load_manifest(Path("tests/fixtures/thinkpad_mini_manifest.yaml"))


def test_domain_reranker_boosts_exact_manual_and_procedure_type() -> None:
    resolution = resolve_thinkpad_model("X1 Carbon Gen 9 battery removal", _manuals())
    results = [
        RetrievalResult(
            chunk_id="wrong",
            score=0.9,
            text="Battery removal",
            metadata={
                "manual_id": "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
                "record_type": "fru_procedure",
                "page_start": 80,
                "source_url": "https://download.lenovo.com/a.pdf",
            },
        ),
        RetrievalResult(
            chunk_id="right",
            score=0.2,
            text="Battery removal",
            metadata={
                "manual_id": "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
                "record_type": "fru_procedure",
                "machine_types": "20XW,20XX",
                "page_start": 81,
                "source_url": "https://download.lenovo.com/b.pdf",
            },
        ),
    ]

    ranked, decisions = rerank_thinkpad_results("X1 Carbon Gen 9 battery removal", results, resolution)

    assert ranked[0].chunk_id == "right"
    assert "manual_match" in ranked[0].metadata["domain_boosts"]
    assert "procedure_boost" in ranked[0].metadata["domain_boosts"]
    assert decisions[0].chunk_id == "right"


def test_domain_reranker_boosts_error_table_exact_code() -> None:
    results = [
        RetrievalResult(
            chunk_id="procedure",
            score=0.7,
            text="General procedure",
            metadata={"manual_id": "m1", "record_type": "fru_procedure"},
        ),
        RetrievalResult(
            chunk_id="error",
            score=0.1,
            text="0271 Date and time error",
            metadata={
                "manual_id": "m1",
                "record_type": "table",
                "table_type": "error_code",
                "section_id": "0271",
                "page_start": 30,
                "source_url": "https://download.lenovo.com/c.pdf",
            },
        ),
    ]

    ranked, _ = rerank_thinkpad_results("E15 Gen 2 error code 0271", results)

    assert ranked[0].chunk_id == "error"
    assert "error_table_boost" in ranked[0].metadata["domain_boosts"]
    assert "exact_numeric_id_match" in ranked[0].metadata["domain_boosts"]
