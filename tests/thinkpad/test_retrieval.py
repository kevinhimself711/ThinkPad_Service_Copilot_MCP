from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.core.types import RetrievalResult
from src.thinkpad.manifest import load_manifest
from src.thinkpad.retrieval import retrieve_thinkpad


def _manuals():
    return load_manifest(Path("tests/fixtures/thinkpad_mini_manifest.yaml"))


@dataclass
class _RetrievalSettings:
    fusion_top_k: int = 10


@dataclass
class _Settings:
    retrieval: _RetrievalSettings = field(default_factory=_RetrievalSettings)


class _FakeSearch:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.calls = 0

    def search(self, query: str, top_k: int):
        self.calls += 1
        return self.results[:top_k]


class _DisabledReranker:
    is_enabled = False


def test_retrieve_requires_clarification_for_ambiguous_high_risk_procedure() -> None:
    search = _FakeSearch([])

    response = retrieve_thinkpad(
        query="X1 Carbon battery removal",
        manuals=_manuals(),
        settings=_Settings(),
        hybrid_search=search,
        core_reranker=_DisabledReranker(),
    )

    assert response.clarification_needed is True
    assert response.reason == "generation_required"
    assert response.results == []
    assert search.calls == 0


def test_retrieve_filters_wrong_manual_for_resolved_model() -> None:
    search = _FakeSearch(
        [
            RetrievalResult(
                chunk_id="wrong",
                score=0.99,
                text="Battery removal for Gen 10",
                metadata={
                    "manual_id": "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
                    "record_type": "fru_procedure",
                    "page_start": 77,
                    "source_url": "https://download.lenovo.com/wrong.pdf",
                },
            ),
            RetrievalResult(
                chunk_id="right",
                score=0.1,
                text="Battery removal for Gen 9",
                metadata={
                    "manual_id": "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
                    "record_type": "fru_procedure",
                    "page_start": 70,
                    "source_url": "https://download.lenovo.com/right.pdf",
                },
            ),
        ]
    )

    response = retrieve_thinkpad(
        query="X1 Carbon Gen 9 battery removal",
        manuals=_manuals(),
        settings=_Settings(),
        hybrid_search=search,
        core_reranker=_DisabledReranker(),
        top_k=5,
    )

    assert response.clarification_needed is False
    assert [item["chunk_id"] for item in response.results] == ["right"]
    assert response.results[0]["citation"]["manual_id"] == "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm"
