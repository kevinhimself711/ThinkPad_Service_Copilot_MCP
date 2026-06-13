# Implementation Log

This file is the permanent implementation fact log for ThinkPad Service Copilot MCP. It is intentionally more detailed than Codex final replies.

Rules:

- Record repo-state implementation facts, not intentions.
- Include concrete files, scripts, commands, validation results, risks, and handoff notes.
- Do not record Lenovo manual text, extracted full text, images, vector stores, secrets, or local-only data artifacts.
- If a fact cannot be confirmed from the repo or existing docs, mark it as `not recorded`.
- Keep `docs/EXPERIMENTS.md` for hypotheses and experiment decisions; keep this file for implementation facts.

## Entry Template

```markdown
## Mx: Title

- Date:
- User goal:
- Scope included:
- Scope excluded:

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|

### Interfaces Or Schemas

### Validation

### Deviations And Risks

### Handoff
```

---

## M0: Repository Bootstrap From Upstream

- Date: 2026-06-08
- User goal: Create the personal ThinkPad Service Copilot MCP repository from `jerry-ai-dev/MODULAR-RAG-MCP-SERVER`, preserve upstream relationship, and add minimal ThinkPad project documentation.
- Scope included: upstream baseline, project docs, local data ignore rules, baseline validation.
- Scope excluded: Lenovo HMM download, ThinkPad domain modules, ingestion, vector stores, MCP tool changes.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Added/kept | `AGENTS.md` | Primary Codex instruction file for the ThinkPad HMM vertical. |
| Added | `docs/M0_BASELINE.md` | Records upstream URL, baseline commit, GitHub target, local setup notes, and validation results. |
| Added/organized | `docs/PROJECT_GUIDE.md` | Project guide established as the main project direction document; later consolidated to v2.1 in M2. |
| Added/organized | `docs/FEASIBILITY_REPORT.md` | Feasibility documentation retained from project planning materials. |
| Added/organized | `docs/DEEPENING_DIRECTIONS.md` | Deeper direction notes retained for later Agentic RAG and graph work. |
| Modified | `.gitignore` | Added local data protections for manuals, extracted artifacts, images, vector stores, storage, and Chroma data. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `python -m venv .venv` | Create local Python environment. | Passed, according to `docs/M0_BASELINE.md`. |
| `.venv\Scripts\python -m pip install -U pip` | Upgrade pip. | Passed. |
| `.venv\Scripts\pip install -e ".[dev]"` | Install project with dev dependencies. | Passed. |
| `.venv\Scripts\python -m pytest tests/unit/test_smoke_imports.py` | Confirm upstream baseline imports. | Passed, `22 passed in 1.50s`. |

### Interfaces Or Schemas

M0 did not introduce ThinkPad runtime APIs, MCP tools, ingestion interfaces, or schema changes.

### Validation

Validation is recorded in `docs/M0_BASELINE.md`. The Windows `py` launcher was unavailable, so validation used `python` directly.

### Deviations And Risks

- Direct `git fetch` over HTTPS to GitHub timed out in the M0 shell, while GitHub API access worked.
- The local workspace was populated from the upstream `main` archive for validation and file preparation.
- No Lenovo manuals or extracted manual artifacts were committed.

### Handoff

Proceed to M1 risk-validation spike before building full ThinkPad ingestion or retrieval.

---

## M1: Eight-Manual HMM Risk Spike

- Date: 2026-06-08
- User goal: Validate high-risk HMM ingestion problems with 8 representative official Lenovo manuals before building the full ThinkPad RAG system.
- Scope included: official Lenovo discovery, local download integrity, upstream ingest dry run, PyMuPDF structural scan, spike docs, synthetic parser tests.
- Scope excluded: full ingestion, vector upsert, public MCP tools, answer generation, committed PDFs, committed extracted full text, committed image dumps.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Added | `config/manuals_manifest.example.yaml` | Committed safe manifest example for the 8 MVP HMM targets; real manifest stays under `data/manifests/`. |
| Added | `scripts/thinkpad_discover_manuals.py` | Discovers official Lenovo HMM candidates from product self-repair pages and `recommendmanual`. |
| Added | `scripts/thinkpad_download_manuals.py` | Downloads PDFs locally, validates official Lenovo URLs, checks `Content-Length`, supports HTTP Range resume, and records SHA256. |
| Added | `scripts/thinkpad_spike_inspect.py` | Runs local PyMuPDF structural inspection and writes aggregate spike output under ignored `data/extracted/`. |
| Added | `src/thinkpad/lenovo.py` | Lenovo discovery helpers for GUID chain extraction, recommendmanual URL construction, and manual candidate parsing. |
| Added | `src/thinkpad/spike.py` | Spike parser helpers for table classification, FRU section candidates, prerequisite extraction, and safety marker detection. |
| Added/evolved | `src/thinkpad/manifest.py` | Initial ThinkPad manifest contract; later extended in M2. |
| Added | `tests/thinkpad/test_lenovo_discovery.py` | Synthetic tests for Lenovo discovery parsing without live network calls. |
| Added | `tests/thinkpad/test_spike_parsers.py` | Synthetic tests for table classification, FRU section parsing, prerequisite extraction, and safety marker detection. |
| Added/evolved | `tests/thinkpad/test_manifest.py` | Manifest validation tests; later expanded in M2. |
| Added | `docs/SPIKE_REPORT.md` | M1 aggregate spike report and go/no-go decisions. |
| Added/evolved | `docs/DEV_SPEC_THINKPAD.md` | M1 spike contract; later upgraded to M2 domain contract. |
| Added/evolved | `docs/EXPERIMENTS.md` | Records M1 discovery, download, dry run, full scan, and test experiments. |
| Modified | `pyproject.toml` | Added PyMuPDF dependency for local PDF structure inspection. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `scripts\thinkpad_discover_manuals.py --target-set m1 --output data\manifests\manuals_manifest.yaml` | Discover the 8 official Lenovo HMM PDFs. | Passed; all 8 discovered through self-repair pages and `api/v4/contents/recommendmanual`. |
| `scripts\thinkpad_download_manuals.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\manuals --update-manifest data\manifests\manuals_manifest.yaml` | Download local PDFs and record integrity metadata. | Passed after adding partial-download protection. |
| `scripts\ingest.py --path data\manuals --collection thinkpad_spike --dry-run` | Confirm upstream CLI can see local PDFs without upsert. | Passed; found 8 PDF files. |
| `scripts\thinkpad_spike_inspect.py --manifest data\manifests\manuals_manifest.yaml --output data\extracted\m1_spike_summary.json` | Full structural scan. | Passed; 877 pages scanned. |
| `python -m pytest tests\thinkpad -q` | Synthetic domain tests. | Passed; M1 experiment log records 10 tests at that point. |

### Interfaces Or Schemas

- Established `ManualMetadata` as the manifest-backed manual-level record.
- Established local manifest convention: committed example in `config/`, real manifest in ignored `data/manifests/`.
- Established official source requirement: Lenovo official URLs only.

### Validation

M1 full scan results:

| Metric | Count |
|---|---:|
| Manuals | 8 |
| Total pages | 877 |
| Total PDF bytes | 416,466,848 |
| Table candidates | 768 |
| PyMuPDF structured table candidates | 331 |
| Figure candidates | 773 |
| Raster fallback pages | 591 |
| FRU section candidates | 555 |
| Safety markers | 687 |

### Deviations And Risks

- Lenovo `productcontentslist` and `productmultlanguagelist` were not reliable for the tested product IDs; the working path uses self-repair page GUIDs plus `recommendmanual`.
- Large Lenovo downloads initially produced partial PDFs; downloader logic was strengthened with `Content-Length` checks and HTTP Range resume.
- PyMuPDF found many table candidates, but row/column correctness was not proven in M1.
- Figure extraction still requires embedded image versus raster fallback validation before answers can cite diagrams.
- FRU section regexes are reconnaissance quality, not production parser quality.

### Handoff

Proceed to M2 domain schemas, manifest validation, and model resolver before retrieval, MCP tools, or full ingestion.

---

## M2: Domain Data Model, Manifest Validator, And Model Resolver

- Date: 2026-06-09
- User goal: Consolidate `PROJECT_GUIDE_v2` into canonical v2.1 and implement M2 internal Python domain APIs.
- Scope included: domain records, manifest extensions, model resolver, synthetic tests, docs update.
- Scope excluded: retrieval, MCP tools, vector stores, full ingestion, image captioning, FRU graph traversal, new PDF downloads, new full scans.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Replaced | `docs/PROJECT_GUIDE.md` | Consolidated v2.1 canonical guide aligned with M1 actual results and M2 boundaries. |
| Deleted | `docs/PROJECT_GUIDE_v2.md` | Removed draft guide to avoid instruction ambiguity. |
| Added | `src/thinkpad/models.py` | Added dataclass records: `Citation`, `TableRecord`, `FigureRecord`, `FRUProcedure`, `WarningRecord`, `DependencyEdge`, `ModelCandidate`, `ModelResolution`. |
| Modified | `src/thinkpad/manifest.py` | Added `page_count`, `product_guids`, status-aware validation, checksum/file-size/page-count rules. |
| Added | `src/thinkpad/model_resolver.py` | Added deterministic resolver for machine type, model+generation, compact aliases, ordinal aliases, ambiguity, and unsupported models. |
| Modified | `src/thinkpad/__init__.py` | Exported M2 domain records and resolver API. |
| Modified | `config/manuals_manifest.example.yaml` | Added `page_count` and `product_guids` fields to the committed example manifest. |
| Expanded | `tests/fixtures/thinkpad_mini_manifest.yaml` | Added synthetic manifest coverage for T14, X1 Carbon, X1 Yoga, E14, and E15 cases. |
| Replaced/expanded | `tests/thinkpad/test_manifest.py` | Added tests for example manifest, URL/path validation, checksums, duplicate IDs, and status requirements. |
| Added | `tests/thinkpad/test_models.py` | Added schema serialization and citation invariant tests. |
| Added | `tests/thinkpad/test_model_resolver.py` | Added resolver tests for machine type, generation aliases, ambiguity, and unsupported models. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Upgraded from M1 spike contract to M2 domain contract. |
| Modified | `docs/EXPERIMENTS.md` | Added `M2-001` schema/resolver experiment record. |
| Modified | `.gitignore` | Added explicit `data/manifests/` local-data protection. |

### Scripts And Commands

M2 did not add executable scripts.

| Script/Command | Purpose | Result |
|---|---|---|
| `.venv\Scripts\python -m pytest tests\thinkpad -q` | Domain tests. | Passed, 28 tests. |
| `.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Upstream smoke imports. | Passed, 22 tests. |
| `.venv\Scripts\ruff check src\thinkpad tests\thinkpad scripts\thinkpad_*.py` | Lint/check ThinkPad modules, tests, and scripts. | Passed after fixing import ordering. |

### Interfaces Or Schemas

M2 internal Python APIs:

```python
load_manifest(path) -> list[ManualMetadata]
resolve_thinkpad_model(query: str, manuals: list[ManualMetadata]) -> ModelResolution
Citation(...)
TableRecord(...)
FigureRecord(...)
FRUProcedure(...)
WarningRecord(...)
DependencyEdge(...)
```

Key invariants:

- Citation requires `manual_id`, `source_url`, and 1-based page fields.
- Authoritative records must carry matching citation manual IDs.
- `downloaded` and `validated` manifests require checksum, file size, and local path.
- `validated` manifests require `page_count`.
- Resolver must not guess a unique procedure from generationless high-risk model text.

### Validation

Validation is recorded in `docs/EXPERIMENTS.md` as `M2-001`.

### Deviations And Risks

- M2 deliberately avoided retrieval and MCP tools to keep the data contracts stable first.
- The resolver is deterministic and metadata-backed; it does not inspect manual content.
- Section-level model applicability is not yet implemented.
- Table/figure/FRU extraction quality remains an M3 risk.

### Handoff

Proceed to M3 parser and ingestion enhancements using the M2 records as output targets.

---

## DOC-001: Permanent Documentation Asset Workflow

- Date: 2026-06-10
- User goal: Make implementation facts and interview-preparation assets permanent after every milestone implementation.
- Scope included: Codex workflow rules, project-guide documentation boundaries, implementation fact log, interview notes.
- Scope excluded: code logic, tests, retrieval behavior, MCP tools, data ingestion.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Modified | `AGENTS.md` | Added required reading entries and DoD/workflow rules for implementation logs and interview notes. |
| Modified | `docs/PROJECT_GUIDE.md` | Added documentation asset roles and milestone DoD requirements for logs and interview notes. |
| Added | `docs/IMPLEMENTATION_LOG.md` | Created the permanent file-level implementation fact log and backfilled M0-M2. |
| Added locally, not committed | `docs/INTERVIEW_NOTES.md` | Created the private project interview notes and backfilled M0-M2 questions; excluded from Git by request. |

### Scripts And Commands

No implementation scripts were added or changed.

### Interfaces Or Schemas

No runtime interfaces or schemas were changed.

### Validation

Validation run before commit:

```powershell
rg "IMPLEMENTATION_LOG|INTERVIEW_NOTES" AGENTS.md docs/PROJECT_GUIDE.md
rg "M0|M1|M2" docs/IMPLEMENTATION_LOG.md docs/INTERVIEW_NOTES.md
git diff --check
```

Additional validation for the staged M1/M2 code and tests:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q
.\.venv\Scripts\ruff check src\thinkpad tests\thinkpad scripts\thinkpad_*.py
```

Results:

- `tests\thinkpad`: passed, 28 tests.
- `tests\unit\test_smoke_imports.py`: passed, 22 tests.
- `ruff check`: passed.

### Deviations And Risks

- This is a docs-only implementation, so pytest is not required unless code is changed in the same task.
- Interview notes use the father-project interview file as a reference source but do not copy it wholesale.
- `docs/INTERVIEW_NOTES.md` is intentionally local/private and should not be committed.

### Handoff

Future milestone implementations must append to both `docs/IMPLEMENTATION_LOG.md` and `docs/INTERVIEW_NOTES.md` before final delivery.

---

## M3: HMM-Aware Extraction Layer

- Date: 2026-06-10
- User goal: Implement the M3 extraction layer that turns local ThinkPad HMM PDFs into structured candidate records without retrieval, MCP tools, vector upsert, or new downloads.
- Scope included: local PDF loader, table extractor, FRU extractor, figure extractor, safety extractor, extraction orchestrator, CLI, synthetic tests, docs, local full extraction validation.
- Scope excluded: retrieval/reranking, MCP tools, upstream ingestion changes, live LLM/image captioning, vector stores, committed PDFs, committed extracted text, committed images.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Modified | `src/thinkpad/models.py` | Added `HMMPage` and `ExtractionResult` dataclasses with validation and `to_dict()` serialization. |
| Added | `src/thinkpad/hmm_loader.py` | Added PyMuPDF local PDF loader, file existence checks, size/SHA256 integrity checks for downloaded/validated manuals, page text extraction, embedded image count, drawing count, raster fallback signal, image xrefs, and gated PyMuPDF table probing. |
| Added | `src/thinkpad/table_extractor.py` | Added `extract_table_records()` to convert PyMuPDF table blocks and Markdown/text table candidates into row-preserving `TableRecord` objects with citations and parent-section hints. |
| Added | `src/thinkpad/fru_extractor.py` | Added `extract_fru_procedures()` to identify FRU procedure sections, preserve prerequisites, emit `DependencyEdge` records, and avoid treating error-code-like rows such as `0271` as FRU headings. |
| Added | `src/thinkpad/figure_extractor.py` | Added embedded image candidate and raster fallback candidate extraction into `FigureRecord`; image files are written only when `write_images=True`. |
| Added | `src/thinkpad/safety.py` | Added cited `WarningRecord` extraction for DANGER, CAUTION, ESD, battery, and system-board safety signals. |
| Added | `src/thinkpad/extraction.py` | Added `ExtractionOptions`, `extract_manual_artifacts()`, `write_jsonl()`, and `write_summary()` orchestration helpers. |
| Modified | `src/thinkpad/__init__.py` | Exported M3 extraction options, extraction result, HMM page, and extraction entrypoint. |
| Added | `scripts/thinkpad_extract_hmm.py` | Added local extraction CLI with `--manifest`, repeatable `--manual-id`, `--output-dir`, `--max-pages`, and `--write-images`. |
| Added | `tests/thinkpad/test_table_extractor.py` | Added synthetic tests for table row/column preservation and Markdown table fallback. |
| Added | `tests/thinkpad/test_fru_extractor.py` | Added synthetic tests for FRU section boundaries, prerequisite dependency edges, and error-code heading guard. |
| Added | `tests/thinkpad/test_figure_extractor.py` | Added synthetic test for raster fallback figure metadata without writing images. |
| Added | `tests/thinkpad/test_safety.py` | Added synthetic test for cited warning record extraction. |
| Added | `tests/thinkpad/test_extract_cli.py` | Added CLI test that creates a tiny synthetic local PDF under ignored data paths, runs the CLI, checks summary/JSONL output, and removes the local fixture. |
| Modified | `tests/thinkpad/test_models.py` | Added serialization coverage for `HMMPage` and `ExtractionResult`. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Added M3 extraction contracts, module responsibilities, CLI behavior, and M4 handoff. |
| Modified | `docs/EXPERIMENTS.md` | Added M3 synthetic test, smoke extraction, and full 8-manual extraction experiment records. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M3 interview-preparation questions; this file remains private and excluded from Git by user request. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Run ThinkPad synthetic unit tests. | Passed, 36 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Confirm upstream smoke imports still pass. | Passed, 22 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad tests\thinkpad scripts\thinkpad_*.py` | Lint ThinkPad modules, tests, and scripts. | Passed. |
| `.\.venv\Scripts\python scripts\thinkpad_extract_hmm.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\extracted\m3_smoke --max-pages 5` | Quick local CLI smoke over all 8 manuals. | Passed; 8 manuals, 40 pages, 0 failures. |
| `.\.venv\Scripts\python scripts\thinkpad_extract_hmm.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\extracted\m3` | Full local extraction over all 8 M1 PDFs. | Passed; 8 manuals, 877 pages, 0 failures, runtime 665.57 seconds. |
| `git diff --check` | Whitespace/error check before commit. | To be run before M3 commit. |

### Interfaces Or Schemas

M3 internal Python APIs:

```python
load_hmm_pages(manual, pdf_path=None, max_pages=None) -> list[HMMPage]
extract_table_records(manual, pages) -> list[TableRecord]
extract_fru_procedures(manual, pages) -> tuple[list[FRUProcedure], list[DependencyEdge]]
extract_figure_records(manual, pdf_path, pages, output_dir, write_images=False) -> list[FigureRecord]
extract_warning_records(manual, pages) -> list[WarningRecord]
extract_manual_artifacts(manual, options) -> ExtractionResult
```

M3 CLI output contract:

- `tables.jsonl`
- `figures.jsonl`
- `fru_procedures.jsonl`
- `warnings.jsonl`
- `dependency_edges.jsonl`
- `summary.json`

All CLI outputs are local ignored artifacts under `data/extracted/`.

### Validation

Full local extraction summary from `data/extracted/m3/summary.json`:

| Metric | Count |
|---|---:|
| Manuals requested | 8 |
| Manuals succeeded | 8 |
| Manuals failed | 0 |
| Pages | 877 |
| Table records | 797 |
| Figure records | 1285 |
| FRU procedures | 195 |
| Dependency edges | 535 |
| Warning records | 687 |

Generated local artifacts were not committed:

| Local artifact | Size |
|---|---:|
| `data/extracted/m3/tables.jsonl` | 580,554 bytes |
| `data/extracted/m3/figures.jsonl` | 1,327,898 bytes |
| `data/extracted/m3/fru_procedures.jsonl` | 193,069 bytes |
| `data/extracted/m3/warnings.jsonl` | 500,268 bytes |
| `data/extracted/m3/dependency_edges.jsonl` | 211,528 bytes |
| `data/extracted/m3/summary.json` | 2,025 bytes |

### Deviations And Risks

- The first full local extraction exceeded a 5-minute tool timeout when PyMuPDF `find_tables()` was probed too broadly. M3 added a lightweight text gate so table probing runs only on likely table pages.
- Full extraction is still slow at about 11 minutes locally; M4 should consider caching, per-manual incremental runs, or deeper table-parser optimization before frequent regression runs.
- M3 records are extraction candidates, not quality-certified facts. Table row alignment, diagram usefulness, FRU section boundaries, and dependency edges still need targeted review before exact retrieval claims.
- Figure records may represent embedded image candidates or raster fallback candidates. They are not LLM-captioned diagrams in M3.
- No upstream ingestion, retrieval, vector store, MCP tool, or dashboard interface was changed.

### Handoff

Proceed to M4 retrieval/rerank only after selecting representative M3 candidates for manual review. Use M3 JSONL as local candidate input, keep exact facts citation-backed, and avoid exposing procedure answers until model resolution, table priority, safety recall, and FRU prerequisite handling are wired into retrieval behavior.

---

## M4: ThinkPad Retrieval + DashScope Provider Wiring

- Date: 2026-06-10
- User goal: Implement M4 retrieval and rerank planning with Bailian/DashScope embedding/rerank/LLM provider wiring, while keeping MCP tools, answer generation, agents, and FRU graph traversal out of scope.
- Scope included: DashScope providers, provider factory registration, settings fields, M3 JSONL to retrieval chunk builder, local retrieval index builder, ThinkPad retrieval facade, domain reranker, index/query CLIs, synthetic tests, docs, evaluation baseline.
- Scope excluded: live paid embedding/rerank calls by default, final natural-language repair answers, MCP tools, dashboard changes, upstream ingestion replacement, new PDF downloads, committed vector stores, committed extracted text, committed `docs/INTERVIEW_NOTES.md`.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Modified | `config/settings.yaml` | Set blank-key DashScope-oriented defaults for LLM, embedding, and rerank: `qwen3.5-flash`, `text-embedding-v4` with 1024 dimensions, and `qwen3-rerank`; disabled vision captioning for M4. |
| Modified | `src/core/settings.py` | Added optional `api_key` and `base_url` fields to `RerankSettings` and parsed them from YAML. |
| Added | `src/libs/embedding/dashscope_embedding.py` | Added DashScope embedding provider using OpenAI-compatible `/embeddings`, `text-embedding-v4`, `dimensions=1024`, and `DASHSCOPE_API_KEY` environment variable lookup. |
| Modified | `src/libs/embedding/embedding_factory.py` | Registered `dashscope` as a built-in embedding provider. |
| Modified | `src/libs/embedding/__init__.py` | Exported `DashScopeEmbedding` and `DashScopeEmbeddingError`. |
| Added | `src/libs/llm/dashscope_llm.py` | Added DashScope OpenAI-compatible chat provider for `qwen3.5-flash`; M4 only tests provider plumbing with mocked HTTP. |
| Modified | `src/libs/llm/llm_factory.py` | Added lazy registration for the `dashscope` LLM provider. |
| Modified | `src/libs/llm/__init__.py` | Exported `DashScopeLLM` and `DashScopeLLMError` and registered `dashscope` on import. |
| Added | `src/libs/reranker/dashscope_reranker.py` | Added DashScope text reranker for `qwen3-rerank`, mapping returned document indexes back to upstream `RetrievalResult` objects. |
| Modified | `src/libs/reranker/reranker_factory.py` | Added lazy registration for the `dashscope` reranker provider. |
| Modified | `src/libs/reranker/__init__.py` | Exported `DashScopeReranker` and `DashScopeRerankerError`. |
| Added | `src/thinkpad/retrieval_corpus.py` | Added `ThinkPadRetrievalChunk`, JSONL readers, and M3 record renderers for tables, FRU procedures, warnings, and figures. |
| Added | `src/thinkpad/domain_reranker.py` | Added deterministic domain rerank rules for exact machine type/manual, wrong-generation penalties, exact FRU/error/screw identifiers, record-type boosts, warning/diagram/procedure intent, and citation presence. |
| Added | `src/thinkpad/retrieval_index.py` | Added `build_thinkpad_retrieval_index()` with dry-run support, local vector-store upsert, and local BM25 index build under ignored `data/db/bm25/<collection>`. |
| Added | `src/thinkpad/retrieval.py` | Added `retrieve_thinkpad()` facade that resolves model text first, refuses ambiguous high-risk procedure queries, runs upstream hybrid search, applies domain rerank, optionally applies provider rerank, and returns JSON citation evidence. |
| Modified | `src/thinkpad/__init__.py` | Exported M4 retrieval, corpus, and index APIs. |
| Added | `scripts/thinkpad_build_retrieval_index.py` | Added CLI for building or dry-running the M4 retrieval index from local M3 artifacts. |
| Added | `scripts/thinkpad_query_retrieval.py` | Added CLI that returns JSON retrieval evidence for a free-form query without generating a repair answer. |
| Added | `tests/unit/test_dashscope_providers.py` | Added mocked HTTP tests for DashScope embedding, rerank, LLM, missing-key behavior, and provider factory creation. |
| Added | `tests/thinkpad/test_retrieval_corpus.py` | Added corpus-builder and index dry-run tests using synthetic JSONL under ignored local paths. |
| Added | `tests/thinkpad/test_domain_reranker.py` | Added deterministic domain-rerank tests for manual/procedure boosts and exact error-code table boosts. |
| Added | `tests/thinkpad/test_retrieval.py` | Added retrieval-facade tests for ambiguous high-risk clarification and wrong-generation filtering. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Added M4 provider, corpus, indexing, query, and M5 handoff contracts. |
| Modified | `docs/EXPERIMENTS.md` | Added M4 provider, corpus dry-run, retrieval test, settings smoke, lint-scope, and live-provider status experiment records. |
| Added | `docs/EVAL_REPORT.md` | Added M4 retrieval baseline with current metrics, dry-run chunk count, synthetic guardrails, and pending live evaluation plan. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M4 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M4 interview-preparation questions; this file remains private and excluded from Git by user request. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\unit\test_dashscope_providers.py -q` | Validate DashScope provider payloads, response parsing, factory registration, and missing-key errors with mocked HTTP. | Passed, 5 tests. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Run all ThinkPad domain tests including M4 retrieval/corpus/rerank coverage. | Passed, 42 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Confirm upstream smoke imports still pass. | Passed, 22 tests. |
| `.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --dry-run` | Convert local M3 artifacts to M4 chunks without provider settings, credentials, embedding, or vector writes. | Passed; 2964 chunks. |
| `load_settings('config/settings.yaml')` ad hoc script | Validate DashScope-oriented settings load through the real settings entrypoint. | Passed; provider/model fields loaded as expected. |
| `Settings.load('config/settings.yaml')` ad hoc script | Initial settings smoke attempt. | Failed because `Settings.load` is not a project API; corrected to `load_settings`. |
| `.\.venv\Scripts\ruff check src\thinkpad src\libs tests\thinkpad tests\unit scripts\thinkpad_*.py` | Planned broad lint command. | Failed on pre-existing upstream lint debt in legacy files; recorded in `docs/EXPERIMENTS.md` M4-005. |
| Focused M4 `ruff check` over new provider, retrieval, CLI, and test files | Validate M4-owned implementation files without broad upstream style cleanup. | Passed. |
| `git diff --check` | Whitespace/error check before commit. | Passed; only Git CRLF conversion warnings were printed. |

### Interfaces Or Schemas

M4 provider interfaces:

```python
DashScopeEmbedding.embed_texts(texts: list[str]) -> list[list[float]]
DashScopeReranker.rerank(query: str, results: list[RetrievalResult], top_k: int | None = None)
DashScopeLLM.chat(messages: list[Message], **kwargs) -> ChatResponse
```

M4 retrieval/index APIs:

```python
build_retrieval_chunks(extracted_dir, manuals, limit=None) -> list[ThinkPadRetrievalChunk]
build_thinkpad_retrieval_index(..., dry_run=False, force_clear=False) -> RetrievalIndexBuildResult
rerank_thinkpad_results(query, results, model_resolution=None, top_k=None)
retrieve_thinkpad(query, manuals, settings, collection="thinkpad_m4", top_k=5) -> ThinkPadRetrievalResponse
```

Behavior invariants:

- Real DashScope credentials come only from `DASHSCOPE_API_KEY`.
- `--dry-run` must not require provider settings or credentials.
- Ambiguous high-risk procedure queries must return clarification instead of a unique procedure.
- Wrong-generation/manual results are filtered or penalized when model resolution is unambiguous.
- Structured records and citations stay in retrieval metadata.
- M4 returns retrieval evidence JSON only; it does not generate final repair instructions.

### Validation

Dry-run corpus summary:

| Metric | Count |
|---|---:|
| Retrieval chunks | 2964 |
| Embedded chunks | 0 |
| Vector count | 0 |
| BM25 doc count | 0 |

The zero embedding/vector/BM25 counts are expected in dry-run mode.

Test summary:

| Suite | Result |
|---|---|
| `tests\unit\test_dashscope_providers.py` | 5 passed |
| `tests\thinkpad` | 42 passed |
| `tests\unit\test_smoke_imports.py` | 22 passed |
| Focused M4 ruff | Passed |

### Deviations And Risks

- Live provider calls and full local vector/BM25 indexing were not run by default because they require a paid API key and produce ignored local artifacts. This is intentional and recorded in `docs/EXPERIMENTS.md` M4-006.
- The broad planned ruff command currently fails due unrelated upstream lint debt. M4-owned files pass focused ruff.
- M4 domain rerank is deterministic and explainable, but not yet measured against a golden retrieval set.
- M4 retrieval uses M3 extraction candidates. It inherits the M3 caveat that table alignment, figure usefulness, and FRU boundaries still need representative manual review.
- No MCP tools or final answer generation are exposed yet, so M4 cannot be demoed as an end-user repair assistant by itself.

### Handoff

Before M5 MCP tools:

- Run a live small index with `DASHSCOPE_API_KEY` set only in the local shell.
- Record vector/BM25 counts and representative JSON query outputs.
- Create a small golden retrieval set for exact error-code, screw, FRU, safety, and ambiguity cases.
- Design MCP tools around the M4 JSON retrieval evidence rather than around raw text chunks.

---

## Live-001: DashScope Live Validation And Retrieval Hardening

- Date: 2026-06-10
- User goal: Use the provided DashScope/Bailian key for real paid provider tests rather than mocks, validate the current ThinkPad retrieval path against live services, and allow future implementation phases to use paid live tests when technically necessary.
- Scope included: live provider smoke, small live index, full live index, live retrieval smoke, MCP query smoke, batch-size hardening, retry hardening, wrong-manual filter regression fix, docs, implementation log, private interview notes.
- Scope excluded: committing API keys, committing local `data/` indexes, running formal Hit@K/MRR evaluation, generating final repair prose, changing M5 MCP public tool names.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Modified | `AGENTS.md` | Added a live-provider validation policy: paid live tests are allowed when they reduce risk, credentials must stay in environment variables, smallest useful live test first, and results must be recorded in docs. |
| Modified | `src/libs/embedding/dashscope_embedding.py` | Added `MAX_BATCH_SIZE = 10`, exposed `max_batch_size`, and added retry handling for transient request errors and retryable 429/5xx HTTP responses. |
| Modified | `src/thinkpad/retrieval_index.py` | Added `batch_size_used` to build summaries, changed default batch size to 10, and capped requested embedding batches by provider `max_batch_size`. |
| Modified | `scripts/thinkpad_build_retrieval_index.py` | Changed `--batch-size` default to 10 and documented the DashScope live limit. |
| Modified | `src/thinkpad/retrieval.py` | Fixed wrong-manual filtering so resolved model queries return empty evidence when no allowed-manual hits exist instead of falling back to wrong manuals. |
| Modified | `tests/unit/test_dashscope_providers.py` | Added a mocked retry regression test for transient embedding request failures. |
| Modified | `tests/thinkpad/test_retrieval_corpus.py` | Added a synthetic test proving the index builder respects a provider-level maximum batch size. |
| Modified | `tests/thinkpad/test_retrieval.py` | Added a regression test for resolved model queries with only wrong-manual retrieval hits. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Documented DashScope batch-size behavior and provider batch capping in the M4 retrieval/index contract. |
| Modified | `docs/EXPERIMENTS.md` | Added live provider, live index, retrieval smoke, and MCP smoke records with failures and decisions. |
| Modified | `docs/EVAL_REPORT.md` | Added a live validation addendum and clarified that the run is not yet a formal retrieval-quality benchmark. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this live validation implementation record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added live-provider interview questions. This file remains private and excluded from Git by user request. |

### Live Commands And Results

| Command Shape | Purpose | Result |
|---|---|---|
| Python provider smoke with `DASHSCOPE_API_KEY` set in the local shell | Call live embedding, rerank, and LLM providers with minimal inputs. | Passed. Embedding returned 1024 dimensions; rerank selected the battery candidate; LLM returned a minimal response. |
| `.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m5_live_smoke --limit 50 --force-clear` | Build a small paid live index. | Failed at old default batch size 50; DashScope reported the batch must be smaller. |
| Same small index after setting batch size 20 | Test adjusted batch size. | Failed again; the live request shape required batch size no larger than 10. |
| Same small index after setting batch size 10 | Validate small live indexing. | Passed: 50 chunks, 50 embedded records, 50 vector records, 50 BM25 docs. |
| Live query smoke against the small sample | Check ambiguity and model filtering. | Found a bug: resolved Gen9 query could fall back to wrong-manual results when the sample lacked allowed manual hits. |
| `.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --force-clear` | Build the full paid local index. | First run failed after about 222 seconds due a transient remote connection reset. |
| Same full index after retry hardening | Validate full live indexing. | Passed in about 416 seconds: 2964 chunks, 2964 embedded records, 2964 vector records, 2964 BM25 docs. |
| Live retrieval smoke against `thinkpad_m4` | Validate model-aware retrieval with the full live index. | Passed. Ambiguous X1 Carbon query requested clarification; Gen9 and 21CB queries returned expected manuals after filtering fix. |
| MCP `query_thinkpad_service` handler live smoke | Validate M5 tool wrapper over live retrieval. | Passed for `21CB battery removal`: `status=ok`, `isError=False`, 2 expected Gen10 manual results. |

### Interface Or Schema Changes

No MCP tool names or input schemas changed.

`RetrievalIndexBuildResult` now includes:

```python
batch_size_used: int = 0
```

`DashScopeEmbedding` now exposes:

```python
max_batch_size = 10
max_retries = 3
retry_backoff_seconds = 1.0
```

### Test Commands And Results

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_retrieval.py tests\thinkpad\test_retrieval_corpus.py -q` | Passed during focused validation. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_dashscope_providers.py -q` | Passed during focused validation. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Passed, 57 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_dashscope_providers.py -q` | Passed, 6 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Passed, 22 tests. |
| `.\.venv\Scripts\python -m pytest tests\integration\test_mcp_server.py -q` | Passed, 6 tests; existing unknown `image` marker warnings remain. |
| `.\.venv\Scripts\ruff check src\libs\embedding\dashscope_embedding.py src\thinkpad\retrieval.py src\thinkpad\retrieval_index.py scripts\thinkpad_build_retrieval_index.py tests\thinkpad\test_retrieval.py tests\thinkpad\test_retrieval_corpus.py tests\unit\test_dashscope_providers.py` | Passed. |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Passed. |
| `git diff --check` | Passed; Git printed Windows CRLF conversion warnings only. |

### Risks And Follow-Up

- Live provider access is now validated, but retrieval quality is still not formally measured.
- Battery-removal queries currently surface safety warnings strongly; M6 should measure and tune record-type ranking for procedure-intent queries.
- The full local index exists only under ignored `data/db` paths and is not portable through Git.
- If the exposed key was used outside this local test context, the user should rotate it in the provider console; this repository only guarantees it was not written to files or committed.

### Handoff

M6 should use the live `thinkpad_m4` index to build a small golden evaluation set and report Hit@K, MRR, citation accuracy, model/generation accuracy, record-type accuracy, and safety-warning recall before adding answer generation or FRU graph traversal.

---

## M5: ThinkPad-Specific MCP Tools

- Date: 2026-06-10
- User goal: Expose ThinkPad-specific MCP tools over M2-M4 resolver, structured extraction records, and retrieval evidence while avoiding answer generation, Agent workflows, Graph RAG traversal, and live-provider requirements by default.
- Scope included: ThinkPad tool service layer, MCP tool wrappers, default MCP registration, synthetic service tests, MCP registration/handler tests, integration/e2e smoke updates, docs, private interview notes.
- Scope excluded: final repair prose generation, FRU dependency-chain MCP tool, `compare_generations`, live DashScope retrieval/index validation, committed `data/`, committed `docs/INTERVIEW_NOTES.md`.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Added | `src/thinkpad/tool_service.py` | Added `ThinkPadToolService`, standard JSON tool response envelope, manifest fallback, lazy M3 JSONL record loading, model ambiguity guard, exact table/FRU/figure/warning lookups, citation normalization, and M4 retrieval facade wrapper. |
| Added | `src/mcp_server/tools/thinkpad_tools.py` | Added 8 ThinkPad MCP tool definitions, JSON schemas, async handlers, JSON `CallToolResult` formatting, module-level service lazy init, and test injection hook. |
| Modified | `src/mcp_server/protocol_handler.py` | Registered ThinkPad MCP tools in `_register_default_tools()` using the existing upstream `ProtocolHandler.register_tool()` path. |
| Modified | `src/thinkpad/__init__.py` | Exported `ThinkPadToolService` and `ThinkPadToolServiceError`. |
| Added | `tests/thinkpad/test_tool_service.py` | Added service tests for supported-model listing, model ambiguity, machine type resolution, error-code lookup, screw-spec non-inference, FRU procedure ambiguity guard, diagram metadata-only behavior, safety warnings, and retrieval wrapper output. |
| Added | `tests/thinkpad/test_thinkpad_mcp_tools.py` | Added MCP registration/schema tests, handler JSON output test, invalid-params error test, and clarification response test. |
| Modified | `tests/integration/test_mcp_server.py` | Updated tools/list assertions to include ThinkPad MCP tools. |
| Modified | `tests/e2e/test_mcp_client.py` | Updated tools/list assertions for ThinkPad tools and changed the multi-call session test to use lightweight tools that do not require provider credentials. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Added M5 MCP tool contract, standard response envelope, deferred tools, behavior rules, and M6 handoff. |
| Modified | `docs/EXPERIMENTS.md` | Added M5 service/handler tests, MCP registration/e2e smoke, lint/smoke imports, and live retrieval status records. |
| Modified | `docs/EVAL_REPORT.md` | Added M5 MCP tool contract baseline and current non-goals for answer faithfulness and live retrieval metrics. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M5 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M5 interview-preparation questions; this file remains private and excluded from Git by user request. |

### MCP Tools Added

| Tool | M5 Behavior |
|---|---|
| `list_supported_models` | Returns configured manuals, models, generations, and optional machine types. |
| `resolve_thinkpad_model` | Returns manifest-backed resolver candidates and clarification state. |
| `query_thinkpad_service` | Wraps M4 retrieval evidence JSON; live use may require local index and `DASHSCOPE_API_KEY`. |
| `lookup_error_code` | Searches structured table rows for exact error-code matches. |
| `get_fru_procedure` | Requires unambiguous model and returns structured FRU procedure candidates. |
| `get_screw_spec` | Searches structured screw/torque rows and does not infer absent values. |
| `get_related_diagram` | Returns figure metadata and citations only; no image bytes in M5. |
| `get_safety_warnings` | Returns cited warning records for model and optional component. |

Deferred:

- `get_fru_dependency_chain`: deferred to M7 Graph RAG.
- `compare_generations`: deferred until retrieval/evaluation maturity improves.

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_tool_service.py tests\thinkpad\test_thinkpad_mcp_tools.py -q` | Run M5 focused service and MCP handler tests. | Passed, 13 tests. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Run all ThinkPad tests. | Passed, 55 tests. |
| `.\.venv\Scripts\python -m pytest tests\integration\test_mcp_server.py -q` | Confirm stdio MCP server initialization, tools/list, and integration helpers. | Passed, 6 tests; existing unknown `image` marker warnings remain. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_mcp_client.py -q` | Confirm e2e MCP client lifecycle and multi-call session. | Passed, 7 tests after changing the multi-call scenario to lightweight tools. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Confirm upstream smoke imports still pass. | Passed, 22 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Lint M5 ThinkPad/MCP tool scope. | Passed. |
| Extra e2e-inclusive `ruff check` | Check the edited e2e file as well as M5 scope. | Failed on pre-existing pyupgrade findings in `tests\e2e\test_mcp_client.py` (`typing.Dict/List/Optional`); not treated as M5 blocker. |
| `git diff --check` | Whitespace/error check before commit. | Passed; only Git CRLF conversion warnings were printed. |

### Interfaces Or Schemas

M5 standard JSON response shape:

```json
{
  "tool": "tool_name",
  "status": "ok | clarification_required | not_found | error",
  "clarification_needed": false,
  "message": "",
  "model_resolution": {},
  "results": [],
  "citations": [],
  "metadata": {}
}
```

Key service API:

```python
ThinkPadToolService.list_supported_models(include_machine_types=True)
ThinkPadToolService.resolve_thinkpad_model(query)
ThinkPadToolService.query_thinkpad_service(query, top_k=5, collection="thinkpad_m4")
ThinkPadToolService.lookup_error_code(error_code, model=None, top_k=5)
ThinkPadToolService.get_fru_procedure(model, component_or_fru, top_k=5)
ThinkPadToolService.get_screw_spec(model, component_or_screw, top_k=5)
ThinkPadToolService.get_related_diagram(model, component_or_fru, top_k=5, include_images=False)
ThinkPadToolService.get_safety_warnings(model, component=None, top_k=5)
```

### Validation Notes

- M5 exact lookup tools do not require live provider calls.
- `query_thinkpad_service` can return a tool-level error JSON if a live retrieval provider is not configured; this is expected in default no-key environments.
- The first E2E run failed in the multi-call session when `query_knowledge_hub` was used as one of several sequential calls without a DashScope key. The scenario was corrected to test protocol multi-call behavior with lightweight tools instead.

### Deviations And Risks

- M5 does not expose image bytes even when `include_images=true`; it records `image_bytes_returned=false`.
- Exact lookup quality depends on M3 structured record quality.
- `query_thinkpad_service` is only as good as the local M4 index; live retrieval metrics remain unmeasured.
- The default manifest fallback uses `config/manuals_manifest.example.yaml` when local ignored manifest data is unavailable, so default MCP startup remains stable but may reflect planned/example metadata.
- No natural-language repair plan is produced in M5.

### Handoff

Proceed to M6 evaluation/dashboard work: create a small golden tool/retrieval set, measure exact lookup and citation accuracy, run a live limited `thinkpad_m4` index when credentials are explicitly available, and only then consider answer generation or Graph RAG traversal.

---

## M6: ThinkPad Evaluation Baseline + Lightweight Dashboard

- Date: 2026-06-12
- User goal: Implement the M6 eval-first plan by adding a ThinkPad-specific golden set, deterministic evaluation runner, live retrieval baseline, and a lightweight dashboard report viewer.
- Scope included: committed 30-case golden set, evaluation dataclasses/API, CLI, dashboard viewer, unit tests, dashboard smoke tests, structured baseline run, live DashScope retrieval baseline run, docs, implementation log, private interview notes.
- Scope excluded: generated repair answers, Ragas faithfulness, Graph RAG traversal, Agent workflow, new HMM downloads, committed evaluation reports, committed provider outputs, committed `data/`, committed `docs/INTERVIEW_NOTES.md`.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Added | `src/thinkpad/evaluation.py` | Added `ThinkPadGoldenCase`, `ThinkPadEvalResult`, `ThinkPadEvalReport`, golden set loader, evaluator, deterministic metrics, skipped live retrieval handling, and report serialization. |
| Modified | `src/thinkpad/__init__.py` | Exported M6 evaluation dataclasses and functions. |
| Added | `scripts/thinkpad_evaluate.py` | Added CLI for M6 structured and live retrieval evaluation with optional `--require-live-retrieval` and `--output`. |
| Added | `tests/fixtures/thinkpad_m6_golden_set.json` | Added 30 copyright-light ThinkPad cases covering resolver, exact tools, FRU, diagram, safety, negatives, and live retrieval. |
| Added | `tests/thinkpad/test_evaluation.py` | Added tests for golden set validation, duplicate IDs, invalid schema, rank metrics, citation metrics, live retrieval skip behavior, clarification scoring, and JSON-safe report serialization. |
| Added | `src/observability/dashboard/pages/thinkpad_evaluation.py` | Added read-only Streamlit page for viewing local M6 evaluation reports. |
| Modified | `src/observability/dashboard/app.py` | Registered the new ThinkPad Evaluation page in dashboard navigation. |
| Modified | `tests/e2e/test_dashboard_smoke.py` | Added missing-report and synthetic-report smoke tests for the ThinkPad Evaluation page; updated old `List` typing import while touching the file. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Added M6 golden set, API, CLI, metrics, dashboard, and known baseline finding. |
| Modified | `docs/EVAL_REPORT.md` | Added structured and live M6 baseline metrics and the failed screw normalization case. |
| Modified | `docs/EXPERIMENTS.md` | Added M6 golden set, structured evaluation, live retrieval evaluation, and dashboard smoke records. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M6 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M6 interview-preparation notes; remains private and excluded from Git. |

### Golden Set And Metrics

The committed M6 fixture has 30 cases:

- inventory: 1
- model resolution: 4
- model ambiguity: 4
- negative: 4
- error code: 3
- screw spec: 3
- FRU procedure: 3
- diagram: 2
- safety: 2
- live retrieval: 4

M6 metrics:

- `tool_status_accuracy`
- `clarification_accuracy`
- `manual_hit_at_k`
- `manual_mrr`
- `record_type_hit_at_k`
- `record_type_mrr`
- `citation_coverage`
- `citation_accuracy`
- `identifier_hit_at_k`
- `empty_unexpected_result_rate`
- `latency_ms_p50`
- `latency_ms_p95`

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python scripts\thinkpad_evaluate.py --golden-set tests\fixtures\thinkpad_m6_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --top-k 5 --output data\eval\m6_report_structured.json` | Run structured evaluation without live retrieval. | Passed; 30 cases loaded, 26 evaluated, 4 live retrieval cases skipped, 1 evaluated failure. |
| `.\.venv\Scripts\python scripts\thinkpad_evaluate.py --golden-set tests\fixtures\thinkpad_m6_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --top-k 5 --require-live-retrieval --output data\eval\m6_report.json` | Run full M6 evaluation with live DashScope retrieval. | Passed; 30 cases evaluated, 0 skipped, 1 failure. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_evaluation.py -q` | Run M6 evaluator unit tests. | Passed, 9 tests. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Run dashboard smoke including ThinkPad Evaluation page. | Passed, 8 tests. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Run all ThinkPad tests. | Passed, 66 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Run upstream smoke imports. | Passed, 22 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad scripts\thinkpad_*.py tests\thinkpad src\observability\dashboard\pages\thinkpad_evaluation.py tests\e2e\test_dashboard_smoke.py` | Lint M6 scope and touched dashboard smoke test. | Passed. |
| `git diff --check` | Whitespace check. | Passed; Git printed Windows CRLF conversion warnings only. |

Local pytest commands used `TEMP` and `TMP` pointed at `.pytest_tmp` because the default Windows pytest temp root returned `WinError 5` in this session. `.pytest_tmp` is a local generated directory and is not part of the committed project state.

### Baseline Results

Structured run:

| Metric | Value |
|---|---:|
| Evaluated cases | 26 |
| Skipped live retrieval cases | 4 |
| Failed evaluated cases | 1 |
| `tool_status_accuracy` | 0.9615 |
| `manual_hit_at_k` | 0.9444 |
| `manual_mrr` | 0.9000 |
| `record_type_hit_at_k` | 0.9231 |
| `citation_accuracy` | 0.9231 |

Live run:

| Metric | Value |
|---|---:|
| Evaluated cases | 30 |
| Skipped cases | 0 |
| Failed cases | 1 |
| Passed case rate | 0.9667 |
| `tool_status_accuracy` | 0.9667 |
| `manual_hit_at_k` | 0.9500 |
| `manual_mrr` | 0.9100 |
| `record_type_hit_at_k` | 0.9286 |
| `citation_accuracy` | 0.9375 |
| `latency_ms_p95` | 1445.8 |

### Known Failure

`m6_screw_t480_exact_size` expected an exact screw-spec hit for `M2 x 3`, but `get_screw_spec` returned `not_found`.

Interpretation:

- The extracted HMM row uses the multiplication sign `×`.
- The user-style query uses ASCII `x`.
- Current exact structured lookup does not normalize these equivalent screw-size forms.

This is a real M6 finding and should be fixed as a follow-up rather than hidden by loosening the golden set.

### Risks And Handoff

- M6 evaluates evidence quality, not generated answer quality.
- Local reports under `data/eval/` are ignored and not portable through Git.
- The dashboard page is intentionally read-only and does not replace CLI evaluation.
- M6 exposes one exact lookup normalization gap; a targeted follow-up should normalize screw specs before M7 Graph RAG.
- M7 should only proceed after deciding whether to fix the screw normalization gap first or carry it as a known evaluation baseline failure.

---

## M6.1: Sync M6 Commit + Screw-Spec Normalization Fix

- Date: 2026-06-12
- User goal: Push the already-created M6 commit, then fix the M6 screw-spec normalization failure and re-run the same structured and live golden-set evaluations.
- Scope included: pushed M6 to remote, patched structured lookup normalization, added regression tests, re-ran structured and live M6 evaluations, updated evaluation/experiment/implementation docs, updated private interview notes locally.
- Scope excluded: MCP schema changes, new golden cases, new HMM downloads, Graph RAG, answer generation, committed `data/eval/` reports, committed provider outputs, committed `docs/INTERVIEW_NOTES.md`.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Modified | `src/thinkpad/tool_service.py` | Added `_normalize_lookup_text()` and routed `_contains_text()` through normalized record/query strings. The helper normalizes multiplication sign and `*` to `x`, collapses screw-size spacing such as `M2 x 3` into `m2x3`, and preserves the separate exact-code path. |
| Modified | `tests/thinkpad/test_tool_service.py` | Updated the synthetic screw row to use `M2 × 3 mm`, added coverage for `M2 x 3`, `M2*3`, and `M2x3 mm`, and added a regression assertion that `271` does not match exact error code `0271`. |
| Modified | `docs/EVAL_REPORT.md` | Added M6.1 before/after metrics for structured and live runs. |
| Modified | `docs/EXPERIMENTS.md` | Added M6.1 push, unit, structured regression, and live regression experiment records. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M6.1 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M6.1 interview-preparation questions about evaluation remediation and exact lookup normalization. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `git push origin thinkpad-hmm-domain` | Sync the existing M6 commit to remote before starting M6.1. | Passed; remote advanced to `1597bef test(thinkpad): add M6 evaluation baseline`. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_tool_service.py tests\thinkpad\test_evaluation.py -q` | Focused regression tests for tool service normalization and evaluator behavior. | Passed, 19 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad\tool_service.py tests\thinkpad\test_tool_service.py` | Focused lint for the changed code/tests. | Passed. |
| `.\.venv\Scripts\python scripts\thinkpad_evaluate.py --golden-set tests\fixtures\thinkpad_m6_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --top-k 5 --output data\eval\m6_report_structured.json` | Re-run structured M6 golden set without live retrieval. | Passed; 26 evaluated, 4 live retrieval cases skipped, 0 failures. |
| `.\.venv\Scripts\python scripts\thinkpad_evaluate.py --golden-set tests\fixtures\thinkpad_m6_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --top-k 5 --require-live-retrieval --output data\eval\m6_report.json` | Re-run full M6 golden set with live DashScope retrieval. | Passed; 30 evaluated, 0 skipped, 0 failures. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Run all ThinkPad tests after the remediation. | Passed, 68 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Run upstream smoke imports. | Passed, 22 tests. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Run dashboard smoke tests. | Passed, 8 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad scripts\thinkpad_*.py tests\thinkpad src\observability\dashboard\pages\thinkpad_evaluation.py tests\e2e\test_dashboard_smoke.py` | Lint the M6.1 scope and existing dashboard smoke scope. | Passed. |
| `git diff --check` | Check whitespace before staging. | Passed; Git printed Windows CRLF conversion warnings only. |
| Working diff secret scan for provider-key patterns | Ensure no provider key was written to tracked diff. | Passed. |

### Before And After Evidence

| Run | Evaluated | Skipped | Failed | `tool_status_accuracy` | `manual_hit_at_k` | `citation_accuracy` |
|---|---:|---:|---:|---:|---:|---:|
| M6 structured baseline | 26 | 4 | 1 | 0.9615 | 0.9444 | 0.9231 |
| M6 live baseline | 30 | 0 | 1 | 0.9667 | 0.9500 | 0.9375 |
| M6.1 structured after fix | 26 | 4 | 0 | 1.0000 | 1.0000 | 1.0000 |
| M6.1 live after fix | 30 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

### Deviations And Risks

- The M6 golden set was intentionally not modified; this keeps the before/after comparison honest.
- Normalization is currently targeted at text lookup terms and common screw-size forms. It does not attempt a full units parser.
- Live retrieval p95 latency increased in this run to `6268.05 ms`; this is recorded as runtime/provider variation and does not change the retrieval-quality interpretation.
- Local reports under `data/eval/` remain ignored and are not committed.

### Handoff

After final validation and commit, M7 can proceed to FRU dependency graph planning. Keep M6/M6.1 golden evaluation as a regression suite before and after graph traversal changes.

---

## M7: FRU Dependency Graph + MCP Tool

- Date: 2026-06-12
- User goal: Implement lightweight FRU dependency graph traversal over M3 `fru_procedures.jsonl` and `dependency_edges.jsonl`, expose it through MCP as `get_fru_dependency_chain`, and extend evaluation without answer generation or Agent workflow.
- Scope included: standard-library graph layer, tool service dependency-edge loading, MCP schema/handler, M7 golden set, evaluator support, synthetic tests, structured graph evaluation, docs, private interview notes.
- Scope excluded: graph database, natural-language repair plans, Agent workflow, new HMM downloads, retrieval index changes, committed `data/`, committed `docs/INTERVIEW_NOTES.md`.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Added | `src/thinkpad/fru_graph.py` | Added `FRUDependencyGraph` and `build_fru_dependency_graph()` for deterministic in-memory traversal, missing-node reporting, max-depth truncation, and cycle detection. |
| Modified | `src/thinkpad/tool_service.py` | Added lazy `dependency_edges` loading and `get_fru_dependency_chain()` backed by model guard, structured FRU lookup, and graph traversal. |
| Modified | `src/mcp_server/tools/thinkpad_tools.py` | Registered MCP tool `get_fru_dependency_chain` with JSON schema and async handler. |
| Modified | `src/thinkpad/evaluation.py` | Added evaluator support for `get_fru_dependency_chain` and M7 report versioning when graph cases are present. |
| Modified | `src/thinkpad/__init__.py` | Exported graph API symbols. |
| Added | `tests/fixtures/thinkpad_m7_golden_set.json` | Copied M6 cases and added 6 M7 graph cases for battery, system board, exact FRU ID, ambiguity, and negative lookup. |
| Added | `tests/thinkpad/test_fru_graph.py` | Added graph unit tests for direct chain, multi-hop chain, missing nodes, cycles, and missing target. |
| Modified | `tests/thinkpad/test_tool_service.py` | Added dependency-edge fixtures and tests for graph evidence, ambiguity, and not-found behavior. |
| Modified | `tests/thinkpad/test_thinkpad_mcp_tools.py` | Added new tool registration and handler JSON tests. |
| Modified | `tests/thinkpad/test_evaluation.py` | Added evaluator test for the dependency-chain tool and no-`top_k` injection behavior. |
| Modified | `tests/integration/test_mcp_server.py` | Added tools/list assertion for `get_fru_dependency_chain`. |
| Modified | `tests/e2e/test_mcp_client.py` | Added tools/list assertion for `get_fru_dependency_chain`. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Added M7 graph API, MCP tool, behavior, and evaluation contract. |
| Modified | `docs/EVAL_REPORT.md` | Added M7 structured graph baseline metrics. |
| Modified | `docs/EXPERIMENTS.md` | Added M7 graph test and structured evaluation records. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M7 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M7 interview-preparation questions; remains private and excluded from Git. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_fru_graph.py tests\thinkpad\test_tool_service.py tests\thinkpad\test_thinkpad_mcp_tools.py tests\thinkpad\test_evaluation.py -q` | Focused graph, service, MCP, and evaluator regression tests. | Passed, 34 tests. |
| `.\.venv\Scripts\python scripts\thinkpad_evaluate.py --golden-set tests\fixtures\thinkpad_m7_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --top-k 5 --output data\eval\m7_report_structured.json` | Run M7 structured golden evaluation against local M3 extraction artifacts. | Passed; 32 evaluated, 4 live retrieval cases skipped, 0 failures. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Run all ThinkPad tests after graph changes. | Passed, 78 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Run upstream smoke imports. | Passed, 22 tests. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Run dashboard smoke tests. | Passed, 8 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Lint the M7 implementation scope. | Passed. |
| `git diff --check` | Check whitespace before staging. | Passed; Git printed Windows CRLF conversion warnings only. |
| Working diff secret scan for provider-key patterns | Ensure no provider key was written to tracked diff. | Passed. |

### Baseline Results

| Metric | Value |
|---|---:|
| Query count | 36 |
| Evaluated cases | 32 |
| Skipped live retrieval cases | 4 |
| Failed evaluated cases | 0 |
| `tool_status_accuracy` | 1.0000 |
| `manual_hit_at_k` | 1.0000 |
| `manual_mrr` | 0.9636 |
| `record_type_hit_at_k` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `identifier_hit_at_k` | 1.0000 |

### Deviations And Risks

- M7 uses candidate extraction records from M3. It proves graph traversal mechanics, not manually verified completeness of every FRU chain.
- Graph traversal returns evidence JSON, not ordered technician repair instructions.
- Cycles and missing nodes are reported in response metadata/results rather than thrown as fatal errors.
- Live retrieval is not part of M7 graph evaluation; M7 structured graph cases run without provider credentials.
- Local report `data/eval/m7_report_structured.json` remains ignored and uncommitted.

### Handoff

M8 can build a small repair-planning agent that calls resolver, exact tools, `get_fru_procedure`, `get_fru_dependency_chain`, diagrams, and safety warnings. M8 must separately evaluate generated plan faithfulness and should not treat M7 graph evidence as final prose.

---

## M7.1: M0-M7 Completion Audit And Live Regression

- Date: 2026-06-12
- User goal: Before starting M8, verify whether M0-M7 were truly completed, whether they met expectations, whether any gaps remain, and generate an M0-M7 report. Run a meaningful live test if needed.
- Scope included: audit script, M0-M7 progress report, stale guide status fix, structured and live M7 evaluation, regression commands, evaluation/experiment/log documentation, private interview notes.
- Scope excluded: M8 Agent Client, new MCP tools, new HMM downloads, full index rebuild, committed local data, committed provider outputs, committed `docs/INTERVIEW_NOTES.md`.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Added | `scripts/thinkpad_audit_milestones.py` | Added a local audit fact collector that records git HEAD, key evidence file existence, M3 extraction totals, M6/M7 eval summaries, and golden-set counts into ignored `data/eval/m0_m7_audit.json`. |
| Added | `docs/M0_M7_PROGRESS_AUDIT.md` | Added the canonical M0-M7 completion audit report with verdicts, evidence, limitations, regression results, and M8 readiness decision. |
| Modified | `docs/PROJECT_GUIDE.md` | Replaced stale M0/M1-only repository status with current M0-M7 status and added the audit report as canonical evidence. |
| Modified | `docs/EVAL_REPORT.md` | Added M7.1 structured/live regression results and the pre-M8 audit decision. |
| Modified | `docs/EXPERIMENTS.md` | Added M7.1 audit fact collection, structured regression, live DashScope regression, and final audit verdict experiment records. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M7.1 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M7.1 interview-preparation questions about milestone audit, live validation, and honest risk boundaries. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Initial ThinkPad regression run. | Hit Windows temp-root permission setup error before test bodies. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q --basetemp data\tmp\pytest` | Rerun ThinkPad tests with ignored local pytest temp directory. | Passed, 78 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Verify upstream/domain imports still smoke cleanly. | Passed, 22 tests. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Verify lightweight dashboard page still smokes. | Passed, 8 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Lint ThinkPad code, MCP tools, tests, and scripts including the new audit script. | Passed. |
| `.\.venv\Scripts\python scripts\thinkpad_evaluate.py --golden-set tests\fixtures\thinkpad_m7_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --top-k 5 --output data\eval\m7_report_structured.json` | Run M7 structured evaluation. | Passed; 32 evaluated, 4 live retrieval cases skipped, 0 failures. |
| `.\.venv\Scripts\python scripts\thinkpad_evaluate.py --golden-set tests\fixtures\thinkpad_m7_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --top-k 5 --require-live-retrieval --output data\eval\m7_report_live.json` | Run M7 live DashScope retrieval evaluation using the local environment key only. | Passed; 36 evaluated, 0 skipped, 0 failures. |
| `.\.venv\Scripts\python scripts\thinkpad_audit_milestones.py --output data\eval\m0_m7_audit.json` | Collect local M0-M7 audit facts into ignored JSON. | Passed. |

### Audit Results

| Milestone | Verdict | Key Evidence |
|---|---|---|
| M0 | `complete` | Upstream bootstrap and `docs/M0_BASELINE.md`. |
| M1 | `complete_with_risk` | 8 official Lenovo HMMs scanned locally; extraction quality not fully human-audited. |
| M2 | `complete` | Domain dataclasses, manifest validation, resolver, and tests. |
| M3 | `complete_with_risk` | 8/8 local extraction succeeded with 877 pages and structured candidates. |
| M4 | `complete_with_risk` | Retrieval corpus/index/provider path exists and live retrieval passes current golden set; broader ablation remains future work. |
| M5 | `complete` | ThinkPad MCP evidence tools are registered and tested. |
| M6 | `complete` | Golden evaluation and dashboard baseline exist; M6.1 closed the only M6 failure. |
| M6.1 | `complete` | Screw normalization fix preserved the failing case and made structured/live eval clean. |
| M7 | `complete_with_risk` | FRU graph evidence tool passes structured/live M7 eval; graph edges inherit M3 candidate-extraction risk. |

### Baseline Results

| Run | Evaluated | Skipped | Failed | `tool_status_accuracy` | `manual_hit_at_k` | `manual_mrr` | `citation_accuracy` | `latency_ms_p95` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M7.1 structured | 32 | 4 | 0 | 1.0000 | 1.0000 | 0.9636 | 1.0000 | 16.00 |
| M7.1 live | 36 | 0 | 0 | 1.0000 | 1.0000 | 0.9667 | 1.0000 | 5339.75 |

### Deviations And Risks

- The initial `pytest tests\thinkpad -q` run failed during pytest temp-directory setup because Windows denied access to the default temp root. Rerunning with ignored `data\tmp\pytest` passed and is the meaningful code validation result.
- M7.1 did not rebuild the full `thinkpad_m4` index because the existing ignored local index was present and live evaluation passed.
- M1/M3/M7 remain candidate-extraction milestones; they do not certify every extracted table row, diagram, or dependency edge as manually correct.
- M8 must introduce separate evaluation for generated plan faithfulness and tool-call trajectory quality.

### Handoff

M8 can begin with a small repair-planning agent that orchestrates the existing resolver, exact lookup tools, retrieval evidence, FRU procedure lookup, dependency-chain graph tool, diagrams, and safety warnings. The first M8 deliverable should be agent trajectory evaluation, not a broad productionization push.

---

## M8: Repair-Planning Agent + Scaled Performance Evaluation

- Date: 2026-06-12
- User goal: Implement a local single-agent ThinkPad repair-planning client and replace the small M8 evaluation idea with a 96-case golden benchmark, full live retrieval/LLM baselines, and a stress benchmark.
- Scope included: deterministic agent orchestration, optional live DashScope LLM composition, agent contracts, single-query CLI, benchmark CLI, stress-candidate generator, 96-case fixture, agent evaluator, tests, scaled live evaluation, documentation, private interview notes.
- Scope excluded: new MCP tool, final production answer endpoint, new HMM downloads, committed local reports, committed provider outputs, committed `data/`, committed `docs/INTERVIEW_NOTES.md`.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Added | `src/thinkpad/agent.py` | Added `RepairPlanRequest`, `RepairPlanResult`, `ToolCallTrace`, `EvidenceBundle`, `RepairPlanStep`, `AgentRefusal`, and `plan_thinkpad_repair()` for deterministic orchestration plus optional LLM evidence rewriting. |
| Added | `src/thinkpad/agent_evaluation.py` | Added M8 agent golden-set loader, evaluator, per-case result model, report model, deterministic metrics, provider/fallback accounting, latency metrics, and JSON-safe serialization. |
| Modified | `src/thinkpad/__init__.py` | Exported M8 agent and agent-evaluation APIs. |
| Added | `scripts/thinkpad_agent_plan.py` | Added single-query CLI for local repair-plan generation with deterministic, live retrieval, and live LLM flags. |
| Added | `scripts/thinkpad_agent_evaluate.py` | Added 96-case benchmark CLI with deterministic, live retrieval, live LLM, offset/limit, and progress JSONL support. |
| Added | `scripts/thinkpad_generate_agent_eval_candidates.py` | Added local stress-candidate generator from M3 JSONL records; outputs ignored non-gold stress cases under `data/eval/`. |
| Added | `tests/fixtures/thinkpad_m8_agent_golden_set.json` | Added 96 copyright-light agent cases across 8 manuals and 9 evaluation categories. |
| Added | `tests/thinkpad/test_agent.py` | Added tests for ambiguity refusal, machine-type plan trajectory, screw-only lookup behavior, unsupported model LLM avoidance, and fake LLM unsupported-claim detection. |
| Added | `tests/thinkpad/test_agent_evaluation.py` | Added tests for fixture validation, metric calculation, forbidden-tool detection, and provider-error accounting. |
| Added | `docs/M8_AGENT_PERFORMANCE_BASELINE.md` | Added human-readable M8 performance report with deterministic, live retrieval, live LLM, and stress results. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Added M8 agent API, contracts, behavior rules, CLIs, and evaluation requirements. |
| Modified | `docs/EVAL_REPORT.md` | Added M8 baseline metrics and interpretation separating evidence-tool, agent trajectory, and generated-plan quality. |
| Modified | `docs/EXPERIMENTS.md` | Added M8 test, deterministic, live retrieval, live LLM, and stress experiment records. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M8 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M8 interview-preparation questions about agent orchestration, scaled evaluation, live LLM failures, and metric interpretation. |

### Agent Behavior

| Behavior | Implementation Fact |
|---|---|
| Model guard | The agent calls resolver first and returns `clarification_required` for ambiguous high-risk model/generation queries. |
| Exact facts | Error codes, screw specs, FRU procedures, diagrams, warnings, and dependency chains are obtained from existing structured evidence tools. |
| Retrieval | Live retrieval is optional and explicit; the benchmark CLI reuses the local `thinkpad_m4` index and cached retriever setup. |
| LLM | LLM composition is optional and uses evidence-only prompts; missing citations, unsupported identifiers, and provider errors are recorded in validation. |
| Safety | Safety-warning cases require `get_safety_warnings` and cited warning evidence. |
| Refusal | Unsupported models and ambiguous model queries do not proceed to unique repair plans or LLM composition. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_agent.py tests\thinkpad\test_agent_evaluation.py -q --basetemp data\tmp\pytest_m8_agent` | Focused M8 agent and evaluator tests. | Passed, 9 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad\agent.py src\thinkpad\agent_evaluation.py tests\thinkpad\test_agent.py tests\thinkpad\test_agent_evaluation.py scripts\thinkpad_agent_*.py` | Focused lint for M8 code/tests/scripts. | Passed. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --output data\eval\m8_agent_report_deterministic.json --progress-jsonl data\eval\m8_agent_progress_deterministic.jsonl` | Run deterministic 96-case agent baseline. | Passed; 96 cases, 0 failures. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --output data\eval\m8_agent_report_live_retrieval.json --progress-jsonl data\eval\m8_agent_progress_live_retrieval.jsonl` | Run full 96-case live DashScope retrieval baseline. | Passed; 96 cases, 0 failures, 4 retrieval fallback events. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --live-llm --output data\eval\m8_agent_report_live_llm.json --progress-jsonl data\eval\m8_agent_progress_live_llm.jsonl` | Run full 96-case live DashScope LLM baseline. | Completed; 96 cases, 5 failures, all live LLM/provider composition or validation failures. |
| `.\.venv\Scripts\python scripts\thinkpad_generate_agent_eval_candidates.py --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --output data\eval\m8_agent_stress_candidates.json --per-manual 32` | Generate local non-gold stress cases from M3 records. | Passed; 194 cases generated. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set data\eval\m8_agent_stress_candidates.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --output data\eval\m8_agent_stress_report_deterministic.json --progress-jsonl data\eval\m8_agent_stress_progress_deterministic.jsonl` | Run deterministic stress benchmark. | Completed; 194 cases, 17 failures. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set data\eval\m8_agent_stress_candidates.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --output data\eval\m8_agent_stress_report_live_retrieval.json --progress-jsonl data\eval\m8_agent_stress_progress_live_retrieval.jsonl` | Run live retrieval stress benchmark. | Completed; 194 cases, 17 failures, 6 retrieval fallback events. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q --basetemp data\tmp\pytest_m8_final` | Final full ThinkPad regression after docs and M8 code were in place. | Passed, 87 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Final upstream/domain smoke import check. | Passed, 22 tests. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Final dashboard smoke check. | Passed, 8 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Final lint check for ThinkPad code, MCP tools, tests, and scripts. | Passed. |

### Baseline Results

| Run | Cases | Failed | Pass Rate | Provider Error Rate | Retrieval Fallback Rate | Unsupported Claim Rate | p95 Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Deterministic 96-case | 96 | 0 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 16 ms |
| Live retrieval 96-case | 96 | 0 | 1.0000 | 0.0000 | 0.0417 | 0.0000 | 6032 ms |
| Live LLM 96-case | 96 | 5 | 0.9479 | 0.0521 | 0.0833 | 0.0521 | 59000 ms |
| Stress deterministic | 194 | 17 | 0.9124 | 0.0000 | 0.0000 | 0.0000 | 16 ms |
| Stress live retrieval | 194 | 17 | 0.9124 | 0.0000 | 0.0309 | 0.0000 | 6047 ms |

### Deviations And Risks

- M8 live LLM did not reach 1.0. Five cases failed and are intentionally recorded as real failures.
- `llm_citation_preservation=0.8611` shows that generated plan faithfulness is a separate problem from evidence retrieval.
- Stress cases are generated from extraction candidates and are not gold truth; failures highlight candidate noise and alias gaps rather than verified answer failures.
- Live retrieval had fallback events due to provider connection resets. The fallback path prevented user-visible failures in the current benchmarks, but this should still be visible in reports.
- The agent remains a local CLI/Python client, not a new MCP server tool.
- Raw local reports, progress JSONL files, stress candidates, and provider outputs remain under ignored `data/eval/`.

### Handoff

M8 is ready for milestone commit after final whitespace and secret checks. M9 should focus on packaging and interview readiness, but the highest-value M8 remediation before demo polish is live LLM composer hardening: retry, stricter structured output, and component alias cleanup from stress failures.

---

## M8.1: Agent Reliability Remediation

- Date: 2026-06-13
- User goal: Remediate M8 live LLM generation failures and stress benchmark failures before M9, without adding MCP tools or hiding provider failures.
- Scope included: LLM composition validation, evidence-only deterministic repair fallback, provider-error scoring semantics, stress pseudo-FRU filtering, component alias cleanup, before/after reports, tests, and live DashScope validation.
- Scope excluded: new `plan_repair` MCP tool, new HMM downloads, committed `data/`, committed provider traces, committed `docs/INTERVIEW_NOTES.md`, production packaging.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Modified | `src/thinkpad/agent.py` | Added `llm_repair_attempts`, strict JSON LLM composition prompt, validation failure classification, deterministic evidence-only repair fallback, recovered provider-error metadata, and component aliases for wireless-WAN/LAN and I/O bracket forms. |
| Modified | `src/thinkpad/agent_evaluation.py` | Passed `llm_repair_attempts` through evaluator and changed provider-error scoring so provider errors remain metrics but do not fail a case when status/evidence/citations are valid. |
| Modified | `scripts/thinkpad_agent_evaluate.py` | Added `--llm-repair-attempts`. |
| Modified | `scripts/thinkpad_agent_plan.py` | Added `--llm-repair-attempts`. |
| Modified | `scripts/thinkpad_generate_agent_eval_candidates.py` | Added stress candidate filtering for diagnostic pseudo-FRUs such as invalid machine UUID and system configuration entries. |
| Modified | `tests/thinkpad/test_agent.py` | Added tests for LLM repair, hard failure on unsupported identifiers, provider-error recovery without secret leakage, and pseudo-FRU filtering. |
| Added | `docs/M8_1_REMEDIATION_REPORT.md` | Added canonical M8.1 before/after report. |
| Modified | `docs/EVAL_REPORT.md` | Added M8.1 summary metrics and interpretation. |
| Modified | `docs/EXPERIMENTS.md` | Added M8.1 unit, deterministic, live retrieval, live LLM, and stress experiment records. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M8.1 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M8.1 interview notes on generation remediation and provider fallback semantics. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_agent.py tests\thinkpad\test_agent_evaluation.py -q --basetemp data\tmp\pytest_m8_1_focused3 -p no:cacheprovider` | Focused agent/evaluator tests after remediation. | Passed, 13 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad\agent.py src\thinkpad\agent_evaluation.py scripts\thinkpad_agent_evaluate.py scripts\thinkpad_agent_plan.py scripts\thinkpad_generate_agent_eval_candidates.py tests\thinkpad\test_agent.py tests\thinkpad\test_agent_evaluation.py` | Focused lint. | Passed. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --output data\eval\m8_1_agent_report_deterministic.json` | M8.1 deterministic 96-case regression. | Passed; 96 cases, 0 failures. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --output data\eval\m8_1_agent_report_live_retrieval.json` | M8.1 live retrieval 96-case regression. | Passed; 96 cases, 0 failures, fallback rate 0.1354. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --live-llm --llm-repair-attempts 1 --output data\eval\m8_1_agent_report_live_llm.json` | M8.1 live LLM 96-case validation. | Passed; 96 cases, 0 failures, `llm_citation_preservation=1.0000`, `unsupported_claim_rate=0.0000`. |
| `.\.venv\Scripts\python scripts\thinkpad_generate_agent_eval_candidates.py --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --output data\eval\m8_1_agent_stress_candidates.json --per-manual 32` | Regenerate ignored local stress candidates after pseudo-FRU filtering. | Passed; 194 stress cases. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set data\eval\m8_1_agent_stress_candidates.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --output data\eval\m8_1_agent_stress_report_deterministic.json` | M8.1 deterministic stress validation. | Completed; 194 cases, 10 failures, down from 17. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set data\eval\m8_1_agent_stress_candidates.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --output data\eval\m8_1_agent_stress_report_live_retrieval.json` | M8.1 live retrieval stress validation. | Completed; 194 cases, 10 failures, fallback rate 0.0258. |

### Before And After Evidence

| Run | M8 Failed | M8.1 Failed | Key Change |
|---|---:|---:|---|
| Deterministic 96-case | 0 | 0 | No regression. |
| Live retrieval 96-case | 0 | 0 | Provider fallback remains visible. |
| Live LLM 96-case | 5 | 0 | Evidence-only repair fallback recovers malformed/missing-citation/provider failures. |
| Stress deterministic 194-case | 17 | 10 | Pseudo-FRU filtering and aliases reduce candidate noise. |
| Stress live retrieval 194-case | 17 | 10 | Remaining failures are structured-procedure alias/applicability gaps. |

### Deviations And Risks

- A first strict-JSON-only live LLM attempt made failures worse, increasing live LLM failures to 32. That run was discarded as an implementation dead end and replaced with deterministic evidence-only fallback after validation.
- A sandboxed live run produced `WinError 10013` socket-permission failures. Valid live results were rerun with network access enabled.
- Provider errors are still counted in `provider_error_rate`; they no longer automatically fail a case when fallback produces valid status, citations, and identifiers.
- Remaining stress failures are not hidden. They are non-gold stress findings around USB board, wireless WAN/LAN, and power button/fingerprint reader procedure aliases.

### Handoff

M8.1 closes the M8 live LLM golden-set blocker. M9 can proceed to packaging and interview readiness, but demo materials should keep provider fallback metrics visible and should not claim stress coverage is fully clean.

---

## M8.2: Evaluation Reality Check + Anti-Inflation Benchmark

- Date: 2026-06-13
- User goal: Re-evaluate why M8.1 produced many `1.0000` metrics, prevent inflated interpretation, and add stricter/raw evaluation before M9.
- Scope included: evaluator strict/raw metrics, CLI flags, 120-case M8.2 fixture, live DashScope strict evaluations, stress strict run, 24-record M3 extraction spot-check, and documentation.
- Scope excluded: changing M8.1 agent behavior, exposing `plan_repair` as MCP, downloading new HMMs, committing local `data/`, committing provider traces, committing `docs/INTERVIEW_NOTES.md`.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Modified | `src/thinkpad/agent_evaluation.py` | Added `strict_live_llm` and `strict_citation` evaluation flags; added `raw_llm_success_rate`, `fallback_recovered_rate`, `provider_clean_rate`, `strict_citation_accuracy`, and `all_step_citation_coverage`; added validation summary fields to per-case result summaries. |
| Modified | `scripts/thinkpad_agent_evaluate.py` | Added `--strict-live-llm` and `--strict-citation` CLI options. |
| Modified | `tests/thinkpad/test_agent_evaluation.py` | Added tests for raw LLM strict failure, provider-error recovery metrics, strict citation failure, and raw live LLM success metrics. |
| Added | `tests/fixtures/thinkpad_m8_2_reality_golden_set.json` | Added 120-case anti-inflation fixture by preserving the M8 96 cases and adding 24 harder cases. |
| Added | `docs/M8_2_EVAL_REALITY_CHECK.md` | Added canonical M8.2 reality-check report with strict metrics and 24 spot-check records. |
| Modified | `docs/EVAL_REPORT.md` | Added M8.2 summary and interpretation. |
| Modified | `docs/EXPERIMENTS.md` | Added M8.2 unit, deterministic strict, live retrieval strict, raw live LLM strict, stress strict, and spot-check records. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M8.2 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M8.2 interview notes about metric inflation and raw-vs-recovered evaluation. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q --basetemp data\tmp\pytest_m8_2_focused2 -p no:cacheprovider` | Focused ThinkPad regression after evaluator changes. | Passed, 95 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad\agent_evaluation.py scripts\thinkpad_agent_evaluate.py tests\thinkpad\test_agent_evaluation.py` | Focused lint for evaluator/CLI/tests. | Passed. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --strict-citation --output data\eval\m8_2_report_deterministic_strict.json` | Run M8.2 deterministic strict benchmark. | Completed; 120 cases, 74 failures, pass rate 0.3833. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --strict-citation --output data\eval\m8_2_report_live_retrieval_strict.json` | Run M8.2 live retrieval strict benchmark. | Completed; 120 cases, 73 failures, pass rate 0.3917, provider error rate 0.0000. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --live-llm --strict-live-llm --strict-citation --offset <0/20/40/60/80/100> --limit 20 --output data\eval\m8_2_report_raw_live_llm_strict_part_<offset>.json` | Run raw live LLM strict benchmark in six chunks after a full single run timed out. | Completed; combined local report has 120 cases, 82 failures, pass rate 0.3167, raw LLM success 0.0417. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set data\eval\m8_1_agent_stress_candidates.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --strict-citation --output data\eval\m8_2_stress_live_retrieval_strict.json` | Run M8.2 stress live retrieval strict benchmark. | Completed; 194 cases, 178 failures, pass rate 0.0825. |
| Local inline PyMuPDF spot-check script over ignored PDFs and M3 JSONL | Validate sampled M3 records point to real pages/signals. | Completed; 24 records sampled across 8 manuals, 24 pass. |

### Evaluation Results

| Run | Cases | Failed | Pass Rate | Strict Citation Accuracy | Raw LLM Success | Provider Clean |
|---|---:|---:|---:|---:|---:|---:|
| deterministic strict | 120 | 74 | 0.3833 | 0.2708 | n/a | 1.0000 |
| live retrieval strict | 120 | 73 | 0.3917 | 0.3021 | n/a | 1.0000 |
| raw live LLM strict | 120 | 82 | 0.3167 | 0.3021 | 0.0417 | 1.0000 |
| stress live retrieval strict | 194 | 178 | 0.0825 | 0.1031 | n/a | 1.0000 |

### Deviations And Risks

- The first full raw live LLM strict command timed out after 20 minutes. It was rerun as six 20-case chunks and combined locally.
- Strict citation scoring is intentionally harsh and exposes that the current fixture does not yet encode per-step expected citation pages/record types.
- The low raw LLM strict score is expected and should be presented honestly. It does not invalidate M8.1 recovered behavior.
- M8.2 hard cases expose alias, generation-interference, symptom-query, and unsupported-generation classification gaps.

### Handoff

M8.2 establishes honest metric boundaries before M9. M9 can proceed, but README/demo/interview material must distinguish contract pass rate, raw live LLM quality, recovered user-visible behavior, and strict citation quality.

---

## M8.3: Systematic Diagnosis + Usability-Level Optimization

- Date: 2026-06-13
- User goal: Improve the M8.2 strict/raw findings into a usable, explainable benchmark baseline before deciding whether to enter M9.
- Scope included: evaluator semantic repair, agent repair-step granularity, component alias remediation, unsupported-generation classification, screw-size normalization, strict/live/stress evaluation reruns, and documentation.
- Scope excluded: new MCP `plan_repair` tool, new HMM downloads, committed local `data/`, committed provider outputs, committed `docs/INTERVIEW_NOTES.md`, and raw LLM-only demo exposure.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Modified | `src/thinkpad/agent_evaluation.py` | Reworked strict citation scoring into `per_step_citation_validity`, `required_record_type_coverage`, and `required_evidence_coverage`; made `strict-live-llm` disable LLM repair/fallback for raw provider scoring. |
| Modified | `src/thinkpad/agent.py` | Expanded component aliases, mapped no-power symptoms to battery evidence, returned unsupported generation as `not_found`, generated finer procedure-backed repair steps, filtered extraction noise from procedure actions, and passed compact cited plan structure into the LLM composer. |
| Modified | `src/thinkpad/model_resolver.py` | Added unsupported-generation detection and prevented negated generation text from being treated as a positive model-generation match. |
| Modified | `src/thinkpad/tool_service.py` | Improved lookup normalization for screw multiply signs, decimal screw sizes, hyphen/spacing variants, and storage/SSD terms. |
| Modified | `tests/thinkpad/test_agent.py` | Added tests for procedure action planning, unsupported generation, and component alias behavior. |
| Modified | `tests/thinkpad/test_agent_evaluation.py` | Updated strict citation tests so valid extra cited evidence is allowed while missing required manual/page coverage still fails; verified strict live LLM does not repair. |
| Modified | `tests/thinkpad/test_model_resolver.py` | Added unsupported generation and negated-generation regression coverage. |
| Modified | `tests/thinkpad/test_tool_service.py` | Added screw normalization regression coverage for decimal screw-size rows. |
| Added | `docs/M8_3_OPTIMIZATION_REPORT.md` | Added canonical M8.3 before/after optimization report. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Documented the M8.3 evaluator and agent behavior contract. |
| Modified | `docs/EVAL_REPORT.md` | Added M8.3 metrics, interpretation, and M9 gate recommendation. |
| Modified | `docs/EXPERIMENTS.md` | Added M8.3 test, deterministic, live retrieval, raw live LLM, and stress experiment records. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M8.3 implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M8.3 interview notes on strict metrics, alias remediation, and raw-vs-recovered LLM quality. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` with `TEMP/TMP=data\tmp\sys_temp` | Full ThinkPad regression after M8.3 changes. | Passed, 100 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` with `TEMP/TMP=data\tmp\sys_temp` | Upstream smoke import regression. | Passed, 22 tests. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` with `TEMP/TMP=data\tmp\sys_temp` | Dashboard smoke regression. | Passed, 8 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Lint changed ThinkPad/MCP/script surfaces. | Passed. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --strict-citation --output data\eval\m8_3_report_deterministic_strict.json` | M8.3 deterministic strict benchmark. | Completed; 120 cases, 0 failures, pass rate 1.0000. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --strict-citation --output data\eval\m8_3_report_live_retrieval_strict.json` | M8.3 live retrieval strict benchmark. | Completed; 120 cases, 0 failures, provider error rate 0.0000. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --live-llm --strict-live-llm --strict-citation --output data\eval\m8_3_report_raw_live_llm_strict.json` | M8.3 raw live LLM strict benchmark. | Completed; 120 cases, 3 failures, pass rate 0.9750, raw LLM success 0.9375. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set data\eval\m8_1_agent_stress_candidates.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --strict-citation --output data\eval\m8_3_stress_live_retrieval_strict.json` | M8.3 stress live retrieval strict benchmark. | Completed; 194 cases, 6 failures, pass rate 0.9691. |
| `git diff --check` | Whitespace validation. | Passed with line-ending warnings only. |

### Evaluation Results

| Run | Cases | Failed | Pass Rate | Key Metric |
|---|---:|---:|---:|---|
| deterministic strict | 120 | 0 | 1.0000 | `per_step_citation_validity=1.0000` |
| live retrieval strict | 120 | 0 | 1.0000 | `provider_error_rate=0.0000` |
| raw live LLM strict | 120 | 3 | 0.9750 | `raw_llm_success_rate=0.9375` |
| stress live retrieval strict | 194 | 6 | 0.9691 | remaining failures are stress applicability conflicts |

### Deviations And Risks

- The M8.3 recovered live LLM path was not rerun after documentation because `DASHSCOPE_API_KEY` was not present in the current shell. The full raw strict live LLM run was completed and is the stronger new generation-quality signal for this milestone.
- Raw live LLM strict still had 3/120 provider timeout/error failures and p95 latency around 52 seconds.
- The deterministic and live retrieval strict 1.0000 results are benchmark-contract results. They must not be presented as universal open-world repair accuracy.
- Remaining stress failures are generated-candidate applicability conflicts, not broad citation plumbing or retrieval failures.

### Handoff

M8.3 reaches the threshold to proceed to M9 packaging and interview readiness if M9 keeps deterministic validation and recovered evidence fallback as the default repair-planning path. Raw LLM-only planning should remain a reported provider-quality mode, not the demo default.

---

## M8.4a: Human Gold Review Pack

- Date: 2026-06-13
- User goal: Prepare a human-reviewable candidate pack for M8.4 human gold evaluation before changing evaluator page scoring or committing a human gold fixture.
- Scope included: local ignored review-pack generator, synthetic tests, review guide, experiment log, and implementation log.
- Scope excluded: evaluator page-metric changes, committed `thinkpad_m8_4_human_gold_set.json`, live DashScope runs, LLM calls, new HMM downloads, committed `data/`, and committed `docs/INTERVIEW_NOTES.md`.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Added | `scripts/thinkpad_prepare_human_gold_review.py` | Added a deterministic, read-only candidate generator that reads local M3 JSONL artifacts and manifest metadata, then writes ignored JSON/Markdown review packs under `data/eval/`. |
| Added | `tests/thinkpad/test_human_gold_review.py` | Added synthetic tests for pending review status, copyright-light output, positive candidate required fields, page-free negative candidates, missing extracted-dir errors, and Markdown rendering. |
| Added | `docs/M8_4A_HUMAN_GOLD_REVIEW_GUIDE.md` | Added instructions for manually verifying candidate pages against local PDFs without copying Lenovo manual prose. |
| Modified | `docs/EXPERIMENTS.md` | Added M8.4a review-pack generation and unit-test experiment records. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M8.4a implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M8.4a interview notes about separating candidate generation from human gold confirmation. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_human_gold_review.py -q --basetemp data\tmp\pytest_m8_4a_fast2` | Focused tests for the review-pack generator. | Passed, 3 tests. |
| `.\.venv\Scripts\ruff check scripts\thinkpad_prepare_human_gold_review.py tests\thinkpad\test_human_gold_review.py` | Focused lint for the new script and tests. | Passed. |
| `.\.venv\Scripts\python scripts\thinkpad_prepare_human_gold_review.py --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --output data\eval\m8_4_human_gold_review.json --markdown-output data\eval\m8_4_human_gold_review.md` | Generate the local ignored M8.4a review pack from real M3 artifacts. | Passed; wrote 18 candidates across 8 manuals. |

### Generated Local Artifacts

| Path | Status |
|---|---|
| `data/eval/m8_4_human_gold_review.json` | Ignored local review pack, not committed. |
| `data/eval/m8_4_human_gold_review.md` | Ignored local human review guide, not committed. |

### Candidate Distribution

| Category | Count |
|---|---:|
| `fru_procedure` | 6 |
| `fru_dependency_chain` | 3 |
| `table` | 4 |
| `supporting_evidence` | 3 |
| `negative` | 2 |

### Deviations And Risks

- M8.4a deliberately does not create a committed human gold fixture. Every generated candidate remains `review_status=pending`.
- The local review pack is derived from M3 extraction candidates, so it is not gold truth until the user manually verifies pages against local PDFs.
- The review pack includes PDF paths and candidate page numbers but no long Lenovo manual text.

### Handoff

The user should review `data/eval/m8_4_human_gold_review.md` and update the ignored JSON review pack with `review_status`, `verified_pages`, and short `reviewer_notes`. M8.4b should consume only `verified` or `corrected` candidates to create the committed human gold fixture and then revise evaluator page scoring.

---

## M8.4b: Human Gold Finalization + Page Metric Integrity

- Date: 2026-06-13
- User goal: Execute the planned M8.4b by finalizing the manually reviewed M8.4a annotations into a committed human gold fixture, revising strict page coverage, running deterministic evaluations, and recording the real result.
- Scope included: Markdown-driven finalizer, committed human gold fixture, evaluator page metric change, finalizer/evaluator tests, deterministic M8.4 evaluations, docs, and regression checks.
- Scope excluded: live DashScope runs because `DASHSCOPE_API_KEY` was not present in the shell, new HMM downloads, committed `data/`, committed provider output, committed `docs/INTERVIEW_NOTES.md`, and remediation of the newly discovered routing/safety extraction issues.

### File-Level Changes

| Change | Path | Implementation Fact |
|---|---|---|
| Added | `scripts/thinkpad_finalize_human_gold.py` | Added a finalizer that parses human annotations from the local M8.4a Markdown review pack, merges them with original JSON candidate metadata, rejects pending annotations, skips rejected cases, requires verified pages for accepted positive cases, writes the committed fixture, and writes an ignored audit JSON. |
| Added | `tests/fixtures/thinkpad_m8_4_human_gold_set.json` | Added the first committed human-reviewed agent fixture: 15 accepted cases, 3 rejected warning false positives excluded. |
| Modified | `src/thinkpad/agent_evaluation.py` | Changed `required_evidence_coverage` so expected pages use `_per_step_page_coverage()` for `fru_procedure` repair steps instead of only checking any result-level citation hit. |
| Modified | `tests/thinkpad/test_agent_evaluation.py` | Added regression coverage for per-step FRU procedure page coverage while ignoring valid warning/figure supporting steps. |
| Added | `tests/thinkpad/test_human_gold_finalizer.py` | Added synthetic tests for Markdown annotations overriding JSON pending state, corrected pages, rejected-case skipping, positive-case page enforcement, pending annotation failure, and copyright-light output. |
| Modified | `scripts/thinkpad_generate_agent_eval_candidates.py` | Moved Windows stdio wrapping from import time into `main()` to stop pytest capture from failing when tests import helper functions. |
| Added | `docs/M8_4_HUMAN_GOLD_REPORT.md` | Added the canonical M8.4b report with human-review outcome, metric semantics, deterministic results, failure root causes, and M8.4c recommendation. |
| Modified | `docs/DEV_SPEC_THINKPAD.md` | Documented the M8.4 human gold contract, strict page metric semantics, known M8.4b results, and M9 gate impact. |
| Modified | `docs/EVAL_REPORT.md` | Added M8.4b human gold metrics and decision. |
| Modified | `docs/EXPERIMENTS.md` | Added M8.4b finalization, human gold evaluation, 120-case regression, tests, lint, and live-provider note. |
| Modified | `docs/IMPLEMENTATION_LOG.md` | Added this M8.4b implementation fact record. |
| Modified locally, not committed | `docs/INTERVIEW_NOTES.md` | Added M8.4b interview notes about human gold, metric inflation, routing gaps, and safety false positives. |

### Scripts And Commands

| Script/Command | Purpose | Result |
|---|---|---|
| `.\.venv\Scripts\python scripts\thinkpad_finalize_human_gold.py --review-json data\eval\m8_4_human_gold_review.json --review-markdown data\eval\m8_4_human_gold_review.md --output tests\fixtures\thinkpad_m8_4_human_gold_set.json --audit-output data\eval\m8_4_human_gold_finalize_audit.json` | Finalize manually reviewed M8.4a annotations into committed human gold fixture. | Passed; 15 accepted, 3 rejected, 2 corrected, 13 verified. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_4_human_gold_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --strict-citation --output data\eval\m8_4_human_det_strict.json` | Evaluate the new human gold fixture. | Completed; 15 cases, 3 failures, pass rate 0.8000. |
| `.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --strict-citation --output data\eval\m8_4_120_det_strict.json` | Ensure old 120-case strict regression remains clean after evaluator change. | Completed; 120 cases, 0 failures, pass rate 1.0000. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q --basetemp data\tmp\pytest_m8_4b_all_thinkpad_2` | Full ThinkPad regression. | Passed, 107 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Upstream/domain smoke import regression. | Passed, 22 tests. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Dashboard smoke regression. | Passed, 8 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad scripts\thinkpad_*.py tests\thinkpad` | Lint changed ThinkPad modules, scripts, and tests. | Passed. |

### Evaluation Results

| Run | Cases | Failed | Pass Rate | Interpretation |
|---|---:|---:|---:|---|
| M8.4 human gold deterministic strict | 15 | 3 | 0.8000 | Human gold exposed dependency-chain routing gap. |
| M8.4 120-case deterministic strict | 120 | 0 | 1.0000 | Existing generated contract fixture remains clean. |

Human gold failures:

- `m8_4_thinkpad_p1_gen4_x1_extreme_gen4_hmm_chain_1030`
- `m8_4_thinkpad_e14_gen2_e15_gen2_hmm_chain_1020`
- `m8_4_thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm_chain_1020`

Root cause: the agent does not currently recognize "prerequisite chain" as a dependency-graph intent, so it does not call `get_fru_dependency_chain`.

### Deviations And Risks

- The manually reviewed Markdown was used as the source of truth because the generated JSON review pack remained pending. This is intentional and documented by the finalizer audit.
- The rejected warning cases are not replaced in M8.4b. They identify a real safety extractor false-positive issue: broad `battery` matching on table-of-contents pages.
- Live DashScope was not run because `DASHSCOPE_API_KEY` was not present in the shell. No key was written into commands or docs.
- The old 120-case suite returning 1.0000 should not override the human gold result. It remains regression coverage, not proof of readiness for M9.

### Handoff

Do not proceed directly to full M9 packaging. The next recommended milestone is M8.4c: fix dependency-chain routing, tighten safety warning extraction, generate/review replacement warning candidates, and rerun the M8.4 human gold gate.
