from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.thinkpad.manifest import load_manifest
from src.thinkpad.retrieval_corpus import build_retrieval_chunks
from src.thinkpad.retrieval_index import build_thinkpad_retrieval_index


def _manuals():
    return load_manifest(Path("tests/fixtures/thinkpad_mini_manifest.yaml"))


def _test_dir(name: str) -> Path:
    path = Path("data/extracted") / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_retrieval_corpus_builds_cited_table_chunk() -> None:
    extracted = _test_dir("test_m4_retrieval_corpus")
    try:
        (extracted / "tables.jsonl").write_text(
            json.dumps(
                {
                    "record_id": "row_1",
                    "manual_id": "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
                    "page": 40,
                    "table_type": "error_code",
                    "columns": ["Symptom or error", "FRU or action"],
                    "row": {"Symptom or error": "0271 Date and time error", "FRU or action": "Run setup"},
                    "citation": {
                        "manual_id": "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
                        "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/tp_x1_carbon_gen9_x1_yoga_gen6_hmm_en.pdf",
                        "page_start": 40,
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        chunks = build_retrieval_chunks(extracted, _manuals())

        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.chunk_id == "table::row_1"
        assert "0271 Date and time error" in chunk.text
        assert chunk.metadata["manual_id"] == "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm"
        assert chunk.metadata["record_type"] == "table"
        assert chunk.metadata["doc_type"] == "thinkpad_hmm_record"
        assert chunk.metadata["table_type"] == "error_code"
        assert chunk.metadata["page_start"] == 40
        assert chunk.metadata["source_url"].startswith("https://download.lenovo.com/")
    finally:
        shutil.rmtree(extracted)


def test_retrieval_index_dry_run_does_not_require_settings() -> None:
    extracted = _test_dir("test_m4_retrieval_index")
    try:
        (extracted / "warnings.jsonl").write_text(
            json.dumps(
                {
                    "warning_id": "warn_1",
                    "manual_id": "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
                    "page": 7,
                    "warning_level": "DANGER",
                    "text": "Disconnect the battery before service.",
                    "citation": {
                        "manual_id": "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
                        "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/tp_x1_carbon_gen9_x1_yoga_gen6_hmm_en.pdf",
                        "page_start": 7,
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        result = build_thinkpad_retrieval_index(
            extracted_dir=extracted,
            manuals=_manuals(),
            dry_run=True,
        )

        assert result.dry_run is True
        assert result.chunk_count == 1
        assert result.embedded_count == 0
    finally:
        shutil.rmtree(extracted)


def test_retrieval_index_caps_batch_size_to_embedding_limit() -> None:
    extracted = _test_dir("test_m5_retrieval_index_batch_cap")
    bm25_dir = Path("data/db/bm25/test_m5_batch_cap")
    if bm25_dir.exists():
        shutil.rmtree(bm25_dir)
    try:
        rows = []
        for index in range(3):
            rows.append(
                json.dumps(
                    {
                        "record_id": f"row_{index}",
                        "manual_id": "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
                        "page": 40 + index,
                        "table_type": "error_code",
                        "columns": ["Symptom or error", "FRU or action"],
                        "row": {
                            "Symptom or error": f"02{index} synthetic error",
                            "FRU or action": "Run setup",
                        },
                        "citation": {
                            "manual_id": "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
                            "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/tp_x1_carbon_gen9_x1_yoga_gen6_hmm_en.pdf",
                            "page_start": 40 + index,
                        },
                    },
                    ensure_ascii=False,
                )
            )
        (extracted / "tables.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")

        class _Embedding:
            max_batch_size = 2

            def __init__(self) -> None:
                self.batch_sizes: list[int] = []

            def embed(self, texts: list[str]) -> list[list[float]]:
                self.batch_sizes.append(len(texts))
                return [[float(len(text))] for text in texts]

        class _VectorStore:
            def __init__(self) -> None:
                self.records: list[dict] = []

            def upsert(self, records: list[dict]) -> None:
                self.records.extend(records)

            def get_collection_stats(self) -> dict[str, int]:
                return {"count": len(self.records)}

        embedding = _Embedding()
        store = _VectorStore()
        result = build_thinkpad_retrieval_index(
            extracted_dir=extracted,
            manuals=_manuals(),
            settings=object(),
            collection="test_m5_batch_cap",
            batch_size=5,
            embedding_client=embedding,
            vector_store=store,
        )

        assert embedding.batch_sizes == [2, 1]
        assert result.batch_size_used == 2
        assert result.embedded_count == 3
        assert result.vector_count == 3
    finally:
        shutil.rmtree(extracted)
        if bm25_dir.exists():
            shutil.rmtree(bm25_dir)
