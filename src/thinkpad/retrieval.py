"""ThinkPad retrieval facade over upstream hybrid search and M4 domain rerank."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from src.core.settings import Settings, resolve_path
from src.core.types import RetrievalResult
from src.thinkpad.domain_reranker import rerank_thinkpad_results
from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.model_resolver import resolve_thinkpad_model
from src.thinkpad.models import ModelResolution


@dataclass(frozen=True)
class ThinkPadRetrievalResponse:
    """JSON-safe M4 retrieval response without generated repair answers."""

    query: str
    clarification_needed: bool
    reason: str | None
    model_resolution: dict[str, Any]
    results: list[dict[str, Any]] = field(default_factory=list)
    domain_rerank: list[dict[str, Any]] = field(default_factory=list)
    rerank_fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)

    def to_json(self) -> str:
        """Return deterministic JSON."""

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def retrieve_thinkpad(
    query: str,
    manuals: list[ManualMetadata],
    settings: Settings,
    collection: str = "thinkpad_m4",
    top_k: int = 5,
    hybrid_search: Any | None = None,
    core_reranker: Any | None = None,
) -> ThinkPadRetrievalResponse:
    """Retrieve ThinkPad HMM records with model resolution and domain rerank."""

    model_resolution = resolve_thinkpad_model(query, manuals)
    if _requires_clarification(query, model_resolution):
        return ThinkPadRetrievalResponse(
            query=query,
            clarification_needed=True,
            reason=model_resolution.reason or "model_clarification_required",
            model_resolution=model_resolution.to_dict(),
            results=[],
            domain_rerank=[],
        )

    search = hybrid_search or _create_hybrid_search(settings, collection)
    initial_top_k = max(top_k * 4, getattr(settings.retrieval, "fusion_top_k", top_k))
    raw_results = search.search(query=query, top_k=initial_top_k)
    if not isinstance(raw_results, list):
        raw_results = raw_results.results

    domain_ranked, first_decisions = rerank_thinkpad_results(
        query=query,
        results=_filter_wrong_manuals(raw_results, model_resolution),
        model_resolution=model_resolution,
        top_k=initial_top_k,
    )

    rerank_fallback = False
    reranked = domain_ranked
    reranker = core_reranker if core_reranker is not None else _create_core_reranker(settings)
    if reranker is not None and getattr(reranker, "is_enabled", False) and domain_ranked:
        rerank_result = reranker.rerank(query=query, results=domain_ranked, top_k=initial_top_k)
        reranked = rerank_result.results
        rerank_fallback = bool(getattr(rerank_result, "used_fallback", False))

    final_results, second_decisions = rerank_thinkpad_results(
        query=query,
        results=reranked,
        model_resolution=model_resolution,
        top_k=top_k,
    )

    return ThinkPadRetrievalResponse(
        query=query,
        clarification_needed=bool(model_resolution.clarification_needed),
        reason=model_resolution.reason,
        model_resolution=model_resolution.to_dict(),
        results=[_result_to_dict(result) for result in final_results],
        domain_rerank=[decision.to_dict() for decision in (second_decisions or first_decisions)],
        rerank_fallback=rerank_fallback,
    )


def _create_hybrid_search(settings: Settings, collection: str) -> Any:
    from src.core.query_engine.dense_retriever import create_dense_retriever
    from src.core.query_engine.hybrid_search import create_hybrid_search
    from src.core.query_engine.query_processor import QueryProcessor
    from src.core.query_engine.sparse_retriever import create_sparse_retriever
    from src.ingestion.storage.bm25_indexer import BM25Indexer
    from src.libs import vector_store as _vector_store_module  # noqa: F401
    from src.libs.embedding.embedding_factory import EmbeddingFactory
    from src.libs.vector_store.vector_store_factory import VectorStoreFactory

    vector_store = VectorStoreFactory.create(settings, collection_name=collection)
    embedding = EmbeddingFactory.create(settings)
    dense = create_dense_retriever(settings, embedding_client=embedding, vector_store=vector_store)
    bm25 = BM25Indexer(index_dir=str(resolve_path(f"data/db/bm25/{collection}")))
    sparse = create_sparse_retriever(
        settings=settings,
        bm25_indexer=bm25,
        vector_store=vector_store,
        index_dir=str(resolve_path(f"data/db/bm25/{collection}")),
    )
    sparse.default_collection = collection
    return create_hybrid_search(
        settings=settings,
        query_processor=QueryProcessor(),
        dense_retriever=dense,
        sparse_retriever=sparse,
    )


def _create_core_reranker(settings: Settings) -> Any | None:
    from src.core.query_engine.reranker import create_core_reranker

    return create_core_reranker(settings=settings)


def _requires_clarification(query: str, model_resolution: ModelResolution) -> bool:
    return bool(model_resolution.clarification_needed and _is_high_risk_procedure_query(query))


def _is_high_risk_procedure_query(query: str) -> bool:
    normalized = query.lower()
    has_action = any(
        term in normalized
        for term in ("remove", "removal", "replace", "replacement", "procedure", "disassemble")
    )
    has_component = any(
        term in normalized
        for term in ("battery", "system board", "fan", "keyboard", "display", "thermal", "speaker")
    )
    return has_action and has_component


def _filter_wrong_manuals(
    results: list[RetrievalResult],
    model_resolution: ModelResolution,
) -> list[RetrievalResult]:
    if model_resolution.clarification_needed:
        return results
    allowed_manual_ids = {candidate.manual_id for candidate in model_resolution.candidates}
    if not allowed_manual_ids:
        return results
    return [result for result in results if result.metadata.get("manual_id") in allowed_manual_ids]


def _result_to_dict(result: RetrievalResult) -> dict[str, Any]:
    return {
        "chunk_id": result.chunk_id,
        "score": result.score,
        "text": result.text,
        "metadata": result.metadata,
        "citation": {
            "manual_id": result.metadata.get("manual_id"),
            "source_url": result.metadata.get("source_url"),
            "page_start": result.metadata.get("page_start"),
            "page_end": result.metadata.get("page_end"),
            "section": result.metadata.get("section"),
            "section_id": result.metadata.get("section_id"),
        },
    }
