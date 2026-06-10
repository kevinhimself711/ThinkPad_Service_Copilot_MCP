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
