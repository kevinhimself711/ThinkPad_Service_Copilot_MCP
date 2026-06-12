# ThinkPad Domain Developer Spec

> Version: M3 extraction contract
> Date: 2026-06-10
> Scope: ThinkPad HMM corpus metadata, citation records, manifest validation, conservative model resolution, and local HMM extraction records.

## 1. M1 Intent

M1 validates whether Lenovo ThinkPad Hardware Maintenance Manuals can be turned into a reliable domain corpus before building full ingestion, retrieval, MCP tools, or graph features.

M1 does not add ThinkPad MCP tools, vector indexes, full extracted text, image dumps, or generated answers. It only adds local corpus tooling and small parser probes that preserve upstream architecture.

## 2. Data Governance

Allowed in Git:

- Official Lenovo source URLs.
- Manifest examples and schema validation code.
- Discovery/download/inspection scripts.
- Aggregate spike counts and engineering decisions.
- Synthetic tests and synthetic parser fixtures.

Not allowed in Git:

- Lenovo HMM PDFs.
- Full extracted Markdown/text.
- Full image/page-render dumps.
- Vector stores or chunk stores containing manual text.
- Secrets or device serial numbers.

All real local artifacts stay under ignored paths:

- `data/manuals/`
- `data/manifests/`
- `data/extracted/`
- `data/images/`

## 3. Manifest Contract

The committed example manifest is `config/manuals_manifest.example.yaml`. Real manifests should be generated locally under `data/manifests/manuals_manifest.yaml`.

Required fields per manual:

- `manual_id`
- `title`
- `models`
- `generations`
- `machine_types`
- `source_type: lenovo_official`
- `source_url`
- `product_page_url`
- `local_pdf_path`
- `document_type: hmm`
- `language`

Optional M1 fields:

- `year`
- `edition`
- `page_count`
- `checksum_sha256`
- `file_size_bytes`
- `product_guids`
- `spike_status`
- `notes`

Validation rules:

- `source_url` and `product_page_url` must be official Lenovo URLs.
- `local_pdf_path` must be repo-relative and stay under `data/manuals/`.
- `checksum_sha256`, when present, must be a 64-character hex digest.
- `file_size_bytes`, when present, must be positive.
- `page_count`, when present, must be positive.
- `spike_status` must be `planned`, `discovered`, `downloaded`, or `validated`.
- `downloaded` and `validated` records require checksum, file size, and local path.
- `validated` records require page count.

## 4. M1 Tooling

Discovery:

```powershell
.\.venv\Scripts\python scripts\thinkpad_discover_manuals.py --target-set m1 --output data\manifests\manuals_manifest.yaml
```

The primary discovery path is:

1. Fetch the Lenovo product self-repair page.
2. Extract product `Guid` and `ParentGuids`.
3. Call Lenovo `api/v4/contents/recommendmanual`.
4. Select `hardwareMaintenanceManual.pdfs`.

Download:

```powershell
.\.venv\Scripts\python scripts\thinkpad_download_manuals.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\manuals --update-manifest data\manifests\manuals_manifest.yaml
```

The downloader validates official Lenovo PDF URLs, compares remote `Content-Length`, supports HTTP Range resume, writes SHA256, and refuses output outside `data/manuals`.

Inspection:

```powershell
.\.venv\Scripts\python scripts\thinkpad_spike_inspect.py --manifest data\manifests\manuals_manifest.yaml --output data\extracted\m1_spike_summary.json
```

The inspector uses PyMuPDF and stores only aggregate structure signals:

- page count and text-bearing page count
- table candidates
- figure/drawing candidates
- raster fallback candidates
- FRU section candidates
- safety warning markers

No full manual text is stored in committed docs.

## 5. M2 Domain Schema Contract

M2 introduces internal Python records under `src/thinkpad/`. These records are not MCP tools yet.

Required domain records:

- `Citation`: required grounding fields `manual_id`, `source_url`, `page_start`, optional `page_end`, `section`, and `section_id`.
- `TableRecord`: one structured table row with preserved columns, row values, page, table type, parent section, and citation.
- `FigureRecord`: one diagram/image/page-render reference with page, optional bbox, caption, surrounding text, storage URI, and citation.
- `FRUProcedure`: procedure ID, FRU ID/name, steps, prerequisites, warnings, related image IDs, and citation.
- `WarningRecord`: safety marker with warning level, text, page, component hint, and citation.
- `DependencyEdge`: directed FRU prerequisite relation with citation.
- `ModelCandidate`: resolver candidate with canonical model, confidence, matching manual, matched signals, generations, and machine types.
- `ModelResolution`: resolver result with candidates, machine type candidates, clarification flag, and reason.

All record classes must support `to_dict()` and return JSON-safe structures.

Grounding invariants:

- Authoritative record types must carry a `Citation`.
- `Citation.manual_id` must match the record `manual_id`.
- Page numbers are 1-based.
- Structured table rows must remain `dict[str, str]`; do not flatten row facts into unstructured text.

## 6. M2 Model Resolver Contract

Public API:

```python
resolve_thinkpad_model(query: str, manuals: list[ManualMetadata]) -> ModelResolution
```

Resolver priority:

1. Exact machine type match, for example `21CB`.
2. Exact model plus generation, for example `X1 Carbon Gen 9`.
3. Compact or ordinal generation aliases, for example `T14 Gen2` and `E15 second gen`.
4. Generationless family names return candidates and `clarification_needed=True`.
5. Unsupported models return no candidates and `clarification_needed=True`.

The resolver must be deterministic and must not use live network calls or LLM calls.

## 7. M2 Handoff To M3

Proceed to M3 with these implementation priorities:

- Keep `ManualMetadata` as the manifest-backed source of manual-level truth.
- Use `Citation`, `TableRecord`, `FigureRecord`, `FRUProcedure`, `WarningRecord`, and `DependencyEdge` as parser output targets.
- Replace spike regexes with tested parser modules before relying on them for answers.
- Add synthetic mini HMM fixtures for exact table rows, FRU prerequisites, and citation metadata.
- Keep the local corpus under `data/`; do not commit PDFs or extracted full text.

## 8. M3 Extraction Layer Contract

M3 introduces a reusable local extraction layer under `src/thinkpad/`. It does not change the upstream ingestion pipeline, MCP tools, retrieval interfaces, vector stores, or dashboard.

Public internal APIs:

```python
load_hmm_pages(manual, pdf_path=None, max_pages=None) -> list[HMMPage]
extract_table_records(manual, pages) -> list[TableRecord]
extract_fru_procedures(manual, pages) -> tuple[list[FRUProcedure], list[DependencyEdge]]
extract_figure_records(manual, pdf_path, pages, output_dir, write_images=False) -> list[FigureRecord]
extract_warning_records(manual, pages) -> list[WarningRecord]
extract_manual_artifacts(manual, options) -> ExtractionResult
```

New M3 records:

- `HMMPage`: one 1-based PDF page with text, source URL, embedded image count, drawing count, raster fallback signal, page size, optional PyMuPDF table blocks, and image xrefs.
- `ExtractionResult`: one manual-level extraction bundle with tables, figures, FRU procedures, warnings, dependency edges, page count, and failures.

Module responsibilities:

- `src/thinkpad/hmm_loader.py`: opens local PDFs with PyMuPDF, enforces local file existence, checks file size and SHA256 for `downloaded` or `validated` manifest entries, extracts text and structural page signals, and only probes `find_tables()` on likely table pages.
- `src/thinkpad/table_extractor.py`: converts PyMuPDF table blocks into row-preserving `TableRecord` objects, with Markdown/text table parsing as a fallback candidate path.
- `src/thinkpad/fru_extractor.py`: slices FRU procedure sections, preserves prerequisites, emits `DependencyEdge` records, and avoids treating numeric error codes such as `0271` as FRU procedure headings.
- `src/thinkpad/figure_extractor.py`: records embedded image candidates and raster fallback candidates. It writes image files only when `write_images=True`.
- `src/thinkpad/safety.py`: emits cited `WarningRecord` objects for DANGER, CAUTION, ESD, battery, and system-board safety signals.
- `src/thinkpad/extraction.py`: orchestrates one-manual extraction and writes deterministic JSONL/summary artifacts for local validation.

M3 CLI:

```powershell
.\.venv\Scripts\python scripts\thinkpad_extract_hmm.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\extracted\m3
```

Optional flags:

- `--manual-id <manual_id>`: extract one or more selected manuals.
- `--max-pages <n>`: cap pages per manual for quick smoke checks.
- `--write-images`: write embedded images and page rasters under ignored `data/extracted/.../images`.

Output files are local-only and ignored:

- `tables.jsonl`
- `figures.jsonl`
- `fru_procedures.jsonl`
- `warnings.jsonl`
- `dependency_edges.jsonl`
- `summary.json`

Behavior rules:

- Missing local PDFs are hard errors for that manual.
- File-size or checksum mismatches are hard errors for `downloaded` and `validated` manifest entries.
- The CLI never downloads PDFs, never calls live LLMs, and never upserts to a vector store.
- Figure records are candidate metadata by default. They are not proof that a diagram is captioned, quality checked, or suitable for final answer generation.
- Table records preserve row/column structure, but real HMM row alignment still requires targeted quality review before exact-answer claims.

## 9. M3 Handoff To M4

M3 proves that the 8 local M1 manuals can be converted into structured candidate artifacts. M4 should not treat all candidates as production-quality facts yet.

Before retrieval/reranking:

- Manually review representative table rows for error-code, FRU, screw, and torque tables.
- Review representative raster fallback pages and embedded image candidates.
- Check FRU section boundaries and dependency edges for high-value demo procedures.
- Decide whether to add `pymupdf_layout`, pdfplumber/Camelot, or a manual-specific table parser for difficult tables.
- Add retrieval-time filters that prefer exact model/machine type and cited structured rows over generic semantic chunks.

## 10. M4 Retrieval And Provider Contract

M4 introduces a local retrieval layer over M3 structured JSONL artifacts. It still does not expose ThinkPad MCP tools, generate repair answers, run agents, or traverse a FRU graph for final plans.

Provider defaults:

- Embedding provider: `dashscope`
- Embedding model: `text-embedding-v4`
- Embedding dimension: `1024`
- Rerank provider: `dashscope`
- Rerank model: `qwen3-rerank`
- LLM provider: `dashscope`
- LLM model: `qwen3.5-flash`

Secret handling:

- DashScope/Bailian API keys must be supplied only through `DASHSCOPE_API_KEY`.
- The project must not write real provider keys to `config/settings.yaml`, `.env`, docs, tests, logs, or commits.
- Mock provider tests must not require live network access or credentials.

New provider modules:

- `src/libs/embedding/dashscope_embedding.py`: OpenAI-compatible embedding call for `text-embedding-v4`.
- `src/libs/reranker/dashscope_reranker.py`: DashScope text rerank call for `qwen3-rerank`.
- `src/libs/llm/dashscope_llm.py`: OpenAI-compatible chat completion provider for `qwen3.5-flash`; M4 only wires the provider and smoke tests it with mocked HTTP.

The settings file may name these providers and blank `api_key` fields, but real execution must resolve credentials from environment variables.

## 11. M4 Retrieval Corpus Contract

M4 reads ignored local M3 artifacts:

- `data/extracted/m3/tables.jsonl`
- `data/extracted/m3/figures.jsonl`
- `data/extracted/m3/fru_procedures.jsonl`
- `data/extracted/m3/warnings.jsonl`

Each M3 record becomes one citation-backed retrieval chunk through `src/thinkpad/retrieval_corpus.py`.

Required chunk metadata:

- `manual_id`
- `manual_title`
- `record_type`
- `models`
- `generations`
- `machine_types`
- `page_start`
- `page_end`
- `section` or `section_id` when available
- `source_url`
- `collection`
- `doc_type: thinkpad_hmm_record`

Record-specific metadata:

- Tables: `table_type`, `columns`, exact row values.
- FRU procedures: `procedure_id`, `fru_id`, `fru_name`, `prerequisites`, `warnings`.
- Warnings: `warning_level`, `component`.
- Figures: `image_id`, `storage_uri`, `related_fru_id`, `related_component`.

Chunk IDs are stable and type-prefixed:

- `table::<record_id>`
- `fru::<procedure_id>`
- `warning::<warning_id>`
- `figure::<image_id>`

The corpus builder must not write copyrighted text to Git. It only reads and writes under ignored local data paths.

## 12. M4 Indexing And Query APIs

Indexing API:

```python
build_thinkpad_retrieval_index(
    extracted_dir,
    manuals,
    settings=None,
    collection="thinkpad_m4",
    limit=None,
    batch_size=10,
    dry_run=False,
    force_clear=False,
)
```

Indexing behavior:

- `--dry-run` builds chunks and reports counts without loading provider settings or requiring credentials.
- Non-dry-run embeds chunks into the local vector store and writes a local BM25 index under ignored `data/db/bm25/<collection>`.
- The default batch size is `10` because live DashScope `text-embedding-v4` indexing rejected larger batches for M3 chunk inputs.
- If the embedding provider exposes `max_batch_size`, the index builder caps requested batches to that value.
- `--force-clear` clears the target vector collection before writing.
- The indexer must not download PDFs, call LLM answer generation, or expose MCP tools.

CLI:

```powershell
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --dry-run
```

Query API:

```python
retrieve_thinkpad(query, manuals, settings, collection="thinkpad_m4", top_k=5)
```

Query behavior:

- Always run `resolve_thinkpad_model()` first.
- If a high-risk procedure query lacks model generation or machine type, return `clarification_needed=True` and do not return a unique procedure.
- Prefer exact machine type, exact model generation, exact manual, exact FRU/error/screw identifiers, structured record type, and complete citations.
- Domain rerank runs around optional provider rerank so semantic reranking cannot silently overrule critical ThinkPad constraints.
- The response is JSON retrieval evidence, not a natural-language repair answer.

Query CLI:

```powershell
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "X1 Carbon Gen 9 battery removal" --collection thinkpad_m4 --top-k 5
```

## 13. M4 Handoff To M5

M4 establishes retrievable, rerankable, citation-backed evidence. Before M5 MCP tools:

- Run a live small index only after setting `DASHSCOPE_API_KEY` in the shell environment.
- Record chunk count, embedding batch count, vector count, and BM25 document count.
- Run the M4 smoke queries and store outputs under ignored local evaluation artifacts.
- Add a small golden retrieval set before exposing service tools.
- Keep final repair answers out of scope until tool schemas, citation preservation, safety handling, and ambiguity handling are tested end to end.

## 14. M5 MCP Tool Contract

M5 exposes ThinkPad HMM evidence through MCP tools. It does not generate final repair prose, run agents, compare generations, or traverse the FRU dependency graph.

Implementation boundaries:

- Business logic lives in `src/thinkpad/tool_service.py`.
- MCP protocol wrappers live in `src/mcp_server/tools/thinkpad_tools.py`.
- The default MCP server registers the ThinkPad tools through `ProtocolHandler.register_tool()`.
- Tool handlers return JSON text content in a standard response envelope.
- Exact lookup tools use M3 structured JSONL records first and do not require live provider calls.
- `query_thinkpad_service` uses the M4 retrieval facade and may require a local index and `DASHSCOPE_API_KEY` for live retrieval.

Registered M5 tools:

- `list_supported_models`
- `resolve_thinkpad_model`
- `query_thinkpad_service`
- `lookup_error_code`
- `get_fru_procedure`
- `get_screw_spec`
- `get_related_diagram`
- `get_safety_warnings`

Deferred tools:

- `get_fru_dependency_chain`: deferred to M7 Graph RAG.
- `compare_generations`: deferred until retrieval evaluation and model applicability are stronger.

Standard tool response shape:

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

Citation fields:

```json
{
  "manual_id": "...",
  "source_url": "...",
  "page_start": 1,
  "page_end": 1,
  "section": null,
  "section_id": null
}
```

Behavior rules:

- Procedure, screw, diagram, and safety tools require a model string.
- Ambiguous high-risk model text returns `status=clarification_required`.
- `lookup_error_code` can run without a model filter, but applies the filter if provided.
- `get_related_diagram` returns metadata and citations only; M5 does not return image bytes.
- Missing local extraction artifacts produce empty structured lookup results rather than server startup failure.
- MCP handler errors must not expose Python tracebacks to clients.

## 15. M5 Handoff To M6

M5 proves that ThinkPad-specific MCP tool contracts and JSON evidence responses are callable. M6 should focus on retrieval/evaluation depth before adding agent behavior:

- Build a small golden retrieval set for MCP tool scenarios.
- Measure exact lookup, model disambiguation, citation accuracy, and safety-warning recall.
- Run a live limited DashScope index only with `DASHSCOPE_API_KEY` set in the local shell.
- Add dashboard or trace views for ThinkPad tool calls if useful.
- Keep final answer generation gated until evidence quality is measured.

## 16. M6 Evaluation Baseline

M6 adds a ThinkPad-specific evaluation path over M5 evidence tools. It does not generate natural-language repair answers, run Ragas, build Graph RAG, or change MCP tool names.

Golden set:

- Canonical committed fixture: `tests/fixtures/thinkpad_m6_golden_set.json`.
- The fixture contains 30 copyright-light cases.
- Cases describe tool inputs and expected structure only: status, clarification flag, manual IDs, record types, identifiers, page/citation requirements, and category.
- The fixture must not include Lenovo manual passages, extracted full text, image dumps, vector records, or provider output.

Evaluation API:

```python
load_thinkpad_golden_set(path) -> list[ThinkPadGoldenCase]
evaluate_thinkpad_cases(cases, service, collection="thinkpad_m4", top_k=5) -> ThinkPadEvalReport
ThinkPadEvalReport.to_dict() -> dict
```

CLI:

```powershell
.\.venv\Scripts\python scripts\thinkpad_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m6_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --top-k 5 `
  --output data\eval\m6_report.json
```

Live retrieval:

- Retrieval cases call `query_thinkpad_service`.
- Without `DASHSCOPE_API_KEY`, retrieval cases are skipped by default and structured tool cases continue.
- With `--require-live-retrieval`, missing live retrieval credentials or provider/index failures should fail the command.
- Live reports are local artifacts under ignored `data/eval/` and are not committed.

Metrics:

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

Dashboard:

- The ThinkPad Evaluation dashboard page is read-only.
- It reads `data/eval/m6_report.json` by default.
- It must not trigger provider calls, rebuild indexes, write reports, or generate answers.

Known M6 baseline finding:

- T480 screw exact lookup with ASCII `x` does not match extracted screw rows that use the multiplication sign `×`.
- This should be treated as a normalization/rerank follow-up, not hidden by changing the golden expectation.
