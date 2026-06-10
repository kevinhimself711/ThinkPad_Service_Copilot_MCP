"""Local ThinkPad retrieval index builder for M4."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.core.settings import Settings, resolve_path
from src.ingestion.embedding.sparse_encoder import SparseEncoder
from src.ingestion.storage.bm25_indexer import BM25Indexer
from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.retrieval_corpus import build_retrieval_chunks, chunks_to_core


@dataclass(frozen=True)
class RetrievalIndexBuildResult:
    """Summary for one local ThinkPad retrieval-index build."""

    collection: str
    chunk_count: int
    embedded_count: int = 0
    bm25_doc_count: int = 0
    vector_count: int = 0
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


def build_thinkpad_retrieval_index(
    extracted_dir: str | Path,
    manuals: list[ManualMetadata],
    settings: Settings | None = None,
    collection: str = "thinkpad_m4",
    limit: int | None = None,
    batch_size: int = 50,
    dry_run: bool = False,
    force_clear: bool = False,
    embedding_client: Any | None = None,
    vector_store: Any | None = None,
) -> RetrievalIndexBuildResult:
    """Build local Chroma + BM25 indexes from M3 extraction artifacts."""

    chunks = build_retrieval_chunks(extracted_dir=extracted_dir, manuals=manuals, limit=limit)
    core_chunks = chunks_to_core(chunks)
    if dry_run:
        return RetrievalIndexBuildResult(
            collection=collection,
            chunk_count=len(core_chunks),
            dry_run=True,
        )
    if settings is None:
        raise ValueError("settings are required when dry_run=False")
    if not core_chunks:
        return RetrievalIndexBuildResult(collection=collection, chunk_count=0)

    from src.libs import vector_store as _vector_store_module  # noqa: F401
    from src.libs.embedding.embedding_factory import EmbeddingFactory
    from src.libs.vector_store.vector_store_factory import VectorStoreFactory

    embedding = embedding_client or EmbeddingFactory.create(settings)
    store = vector_store or VectorStoreFactory.create(settings, collection_name=collection)
    if force_clear and hasattr(store, "clear"):
        store.clear(collection_name=collection)

    embedded_count = 0
    vector_records: list[dict[str, Any]] = []
    for start in range(0, len(core_chunks), batch_size):
        batch = core_chunks[start : start + batch_size]
        vectors = embedding.embed([chunk.text for chunk in batch])
        embedded_count += len(vectors)
        for chunk, vector in zip(batch, vectors):
            vector_records.append(
                {
                    "id": chunk.id,
                    "vector": vector,
                    "metadata": {
                        **chunk.metadata,
                        "text": chunk.text,
                        "chunk_id": chunk.id,
                    },
                }
            )
        store.upsert(vector_records[-len(batch) :])

    sparse = SparseEncoder()
    term_stats = sparse.encode(core_chunks)
    bm25 = BM25Indexer(index_dir=str(resolve_path(f"data/db/bm25/{collection}")))
    bm25.build(term_stats, collection=collection)

    vector_count = 0
    if hasattr(store, "get_collection_stats"):
        try:
            vector_count = int(store.get_collection_stats().get("count", 0))
        except Exception:
            vector_count = len(vector_records)
    else:
        vector_count = len(vector_records)

    return RetrievalIndexBuildResult(
        collection=collection,
        chunk_count=len(core_chunks),
        embedded_count=embedded_count,
        bm25_doc_count=len(term_stats),
        vector_count=vector_count,
        dry_run=False,
    )
