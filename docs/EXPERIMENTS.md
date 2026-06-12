# Experiments

> Experiment log for ThinkPad Service Copilot MCP. Do not record full copyrighted manual text here.

## M1-001: Official Lenovo HMM Discovery

- Date: 2026-06-08
- Hypothesis: The 8 MVP ThinkPad HMM PDFs can be discovered automatically from official Lenovo support pages.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_discover_manuals.py --target-set m1 --output data\manifests\manuals_manifest.yaml
```

- Result: Passed. All 8 HMM PDF URLs were discovered through Lenovo product self-repair pages and `api/v4/contents/recommendmanual`.
- Failure notes: `productcontentslist` and `productmultlanguagelist` returned empty lists for the tested PID forms, so they are not primary discovery sources.
- Decision: Use product self-repair page GUID extraction plus `recommendmanual` as the M1 discovery path.

## M1-002: Local PDF Download Integrity

- Date: 2026-06-08
- Hypothesis: Official PDFs can be downloaded locally under ignored `data/manuals/` and recorded with SHA256.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_download_manuals.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\manuals --update-manifest data\manifests\manuals_manifest.yaml
```

- Result: Passed after adding integrity checks. 8 PDFs downloaded, total local size 416,466,848 bytes.
- Failure notes: Large Lenovo downloads initially completed early and produced partial PDFs. The downloader now checks remote `Content-Length` and resumes incomplete files with HTTP Range requests.
- Decision: Keep size and checksum validation mandatory before any local inspection or ingestion.

## M1-003: Upstream Ingest Dry Run

- Date: 2026-06-08
- Hypothesis: The upstream ingestion CLI can discover the local M1 PDFs without running full upsert.
- Command:

```powershell
.\.venv\Scripts\python scripts\ingest.py --path data\manuals --collection thinkpad_spike --dry-run
```

- Result: Passed. The CLI found 8 PDF files and exited without processing.
- Decision: Preserve upstream ingestion CLI and add ThinkPad-specific ingestion logic around it later.

## M1-004: Full PDF Structure Scan

- Date: 2026-06-08
- Hypothesis: PyMuPDF can provide enough structural signals to decide M2/M3 parser priorities.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_spike_inspect.py --manifest data\manifests\manuals_manifest.yaml --output data\extracted\m1_spike_summary.json
```

- Result: Passed. Full scan covered 877 pages across 8 manuals.
- Metrics:
  - Table candidates: 768.
  - PyMuPDF structured table candidates: 331.
  - Figure candidates: 773.
  - Raster fallback pages: 591.
  - FRU section candidates: 555.
  - Safety markers: 687.
- Failure notes: PyMuPDF emitted a suggestion to use `pymupdf_layout` for better layout analysis. M1 does not add that dependency yet.
- Decision: M2/M3 must implement exact table-record and FRU-section fixtures before generating authoritative answers.

## M1-005: Synthetic Domain Unit Tests

- Date: 2026-06-08
- Hypothesis: The new M1 manifest/discovery/parser contracts can be tested without live Lenovo calls or copyrighted text fixtures.
- Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

- Result: Passed, 10 tests.
- Failure notes: Initial FRU parser tests exposed two bugs: prerequisite FRU rows were misread as headings, and comma-separated FRU references were greedily merged. Both were fixed.
- Decision: Keep synthetic fixtures as the default for parser regression tests.

## M2-001: Domain Schema And Resolver Contracts

- Date: 2026-06-09
- Hypothesis: The M2 domain records, manifest validator, and model resolver can be tested with synthetic metadata only, without live Lenovo calls or copyrighted manual text.
- Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

- Result: Passed, 28 tests.
- Coverage:
  - Manifest accepts the committed M1 example with 877 total pages.
  - Manifest rejects non-Lenovo URLs, absolute or out-of-scope local paths, invalid checksums, duplicate manual IDs, and incomplete downloaded/validated statuses.
  - Citation-backed records serialize to JSON-safe dictionaries and reject missing grounding fields.
  - Resolver handles exact machine type, exact model+generation, compact generation aliases, ordinal generation aliases, generationless ambiguity, and unsupported models.
- Decision: M2 should stay as an internal Python domain API. Retrieval, MCP tools, vector stores, and generated repair answers remain out of scope until later milestones.

## M3-001: Synthetic Extraction Unit Tests

- Date: 2026-06-10
- Hypothesis: HMM extraction modules can preserve table rows, FRU prerequisites, figure fallback signals, safety citations, and CLI summary structure using synthetic fixtures only.
- Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

- Result: Passed, 36 tests.
- Coverage:
  - `HMMPage` and `ExtractionResult` serialization.
  - Table row/column preservation for exact error-code and screw-spec strings.
  - Markdown/text table fallback parsing.
  - FRU section boundaries and prerequisite dependency edges.
  - Guard against misclassifying numeric error-code rows such as `0271` as FRU procedures.
  - Raster fallback figure records without writing image files.
  - DANGER/CAUTION/safety-related warning records with citations.
  - CLI summary and JSONL output using a synthetic local PDF fixture.
- Decision: Synthetic extraction tests are sufficient for M3 regression coverage, but not enough to claim production-quality extraction over real HMMs.

## M3-002: Local Manifest Smoke Extraction

- Date: 2026-06-10
- Hypothesis: The M3 CLI can loop over the local 8-manual manifest and write all expected artifact files without requiring a full scan.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_extract_hmm.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\extracted\m3_smoke --max-pages 5
```

- Result: Passed. All 8 manuals were selected and processed with 5 pages each.
- Metrics:
  - Manuals succeeded: 8.
  - Manuals failed: 0.
  - Pages processed: 40.
- Decision: Keep `--max-pages` as the default local debugging path for quick CLI checks.

## M3-003: Full Local HMM Extraction

- Date: 2026-06-10
- Hypothesis: The M3 extraction layer can process all 8 local M1 PDFs and write ignored structured artifacts without changing upstream ingestion or vector stores.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_extract_hmm.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\extracted\m3
```

- Result: Passed after adding lightweight table-probing gates around PyMuPDF `find_tables()`.
- Runtime: 665.57 seconds on the local Windows environment.
- Metrics from `data/extracted/m3/summary.json`:
  - Manuals requested: 8.
  - Manuals succeeded: 8.
  - Manuals failed: 0.
  - Pages: 877.
  - Table records: 797.
  - Figure records: 1285.
  - FRU procedures: 195.
  - Dependency edges: 535.
  - Warning records: 687.
- Output files:
  - `data/extracted/m3/tables.jsonl`
  - `data/extracted/m3/figures.jsonl`
  - `data/extracted/m3/fru_procedures.jsonl`
  - `data/extracted/m3/warnings.jsonl`
  - `data/extracted/m3/dependency_edges.jsonl`
  - `data/extracted/m3/summary.json`
- Failure notes: The first full run exceeded a 5-minute tool timeout while probing tables too broadly. `hmm_loader.py` was adjusted to call PyMuPDF `find_tables()` only on likely table pages; the full run then completed successfully.
- Interpretation notes: M3 figure records count embedded image candidates and raster fallback metadata; it is not directly comparable to the M1 figure-candidate metric and does not imply caption quality.
- Decision: M4 can consume M3 JSONL candidates for retrieval/rerank experiments, but exact-answer claims still require targeted quality review of representative table, figure, and FRU samples.

## M4-001: DashScope Provider Mock Tests

- Date: 2026-06-10
- Hypothesis: Bailian/DashScope embedding, rerank, and LLM providers can be registered and tested without live network access or credentials.
- Command:

```powershell
.\.venv\Scripts\python -m pytest tests\unit\test_dashscope_providers.py -q
```

- Result: Passed, 5 tests.
- Coverage:
  - Missing `DASHSCOPE_API_KEY` raises a clear provider error without printing a secret.
  - Embedding provider sends `text-embedding-v4` payloads with `dimensions=1024`.
  - LLM provider sends OpenAI-compatible chat-completion payloads for `qwen3.5-flash`.
  - Reranker sends DashScope rerank payloads for `qwen3-rerank` and maps returned indexes back to retrieval results.
  - Embedding, reranker, and LLM factories can create the `dashscope` providers.
- Decision: Provider wiring is safe to commit with mocked HTTP. Live calls remain opt-in and require an environment variable.

## M4-002: Retrieval Corpus Dry Run Over M3 Artifacts

- Date: 2026-06-10
- Hypothesis: M3 JSONL artifacts can be converted into citation-backed retrieval chunks without loading provider settings or credentials.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --dry-run
```

- Result: Passed.
- Output:

```json
{
  "bm25_doc_count": 0,
  "chunk_count": 2964,
  "collection": "thinkpad_m4",
  "dry_run": true,
  "embedded_count": 0,
  "vector_count": 0
}
```

- Decision: M4 has enough local structured corpus surface for retrieval experiments. This result does not prove embedding quality because dry-run does not call the provider or write a vector/BM25 index.

## M4-003: ThinkPad Retrieval Unit Tests

- Date: 2026-06-10
- Hypothesis: The M4 retrieval facade can enforce model clarification, wrong-manual filtering, and domain rerank priorities using synthetic fixtures.
- Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

- Result: Passed, 42 tests.
- M4 coverage added:
  - Corpus builder preserves citation metadata for table chunks.
  - Index dry-run does not require live settings or credentials.
  - Domain rerank boosts exact machine type/manual, structured procedure records, exact error-code rows, and cited records.
  - `X1 Carbon battery removal` returns clarification instead of a unique procedure.
  - `X1 Carbon Gen 9 battery removal` filters wrong-generation manual results when the resolver identifies the correct manual.
- Decision: M4 retrieval guardrails are testable before live indexing.

## M4-004: Settings And Import Smoke

- Date: 2026-06-10
- Hypothesis: The repository can load DashScope-oriented settings and still pass upstream smoke imports.
- Commands:

```powershell
.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q
```

```powershell
@'
from src.core.settings import load_settings
s = load_settings('config/settings.yaml')
print(s.llm.provider, s.llm.model)
print(s.embedding.provider, s.embedding.model, s.embedding.dimensions)
print(s.rerank.enabled, s.rerank.provider, s.rerank.model)
'@ | .\.venv\Scripts\python -
```

- Result: Smoke imports passed, 22 tests.
- Settings output:

```text
dashscope qwen3.5-flash
dashscope text-embedding-v4 1024
True dashscope qwen3-rerank
```

- Failure note: An initial ad hoc command incorrectly tried `Settings.load(...)`, which is not a project API. The correct entrypoint is `load_settings(...)`.
- Decision: DashScope defaults are loadable without storing a real key in configuration.

## M4-005: Lint Scope

- Date: 2026-06-10
- Hypothesis: M4-owned files can pass lint even though the upstream repository has legacy style debt outside the milestone scope.
- Broad command attempted:

```powershell
.\.venv\Scripts\ruff check src\thinkpad src\libs tests\thinkpad tests\unit scripts\thinkpad_*.py
```

- Result: Failed on pre-existing upstream lint debt, including pyupgrade findings in `src/core/settings.py`, blank-line whitespace in legacy factory files, naming findings in `src/libs/reranker/reranker_factory.py`, and old `tests/unit` files unrelated to M4.
- Focused M4 command:

```powershell
.\.venv\Scripts\ruff check src\libs\embedding\dashscope_embedding.py src\libs\llm\dashscope_llm.py src\libs\reranker\dashscope_reranker.py src\thinkpad\retrieval_corpus.py src\thinkpad\domain_reranker.py src\thinkpad\retrieval.py src\thinkpad\retrieval_index.py scripts\thinkpad_build_retrieval_index.py scripts\thinkpad_query_retrieval.py tests\unit\test_dashscope_providers.py tests\thinkpad\test_retrieval_corpus.py tests\thinkpad\test_domain_reranker.py tests\thinkpad\test_retrieval.py
```

- Result: Passed.
- Decision: Do not mix M4 implementation with a broad upstream lint cleanup. Track the broad lint failure as a repository hygiene issue, not as an M4 retrieval defect.

## M4-006: Live Provider And Full Index Status

- Date: 2026-06-10
- Status: Not run by default.
- Reason: Live DashScope embedding/rerank calls require a paid API key and would create local vector/BM25 artifacts under ignored paths. M4 provider correctness is covered by mocked HTTP tests, and corpus size is covered by dry-run.
- Pending validation command when explicitly approved:

```powershell
$env:DASHSCOPE_API_KEY = "<set in local shell only>"
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --limit 50
```

- Decision: Keep live indexing opt-in and never write secrets to repository files.

## M5-001: ThinkPad Tool Service And MCP Handler Tests

- Date: 2026-06-10
- Hypothesis: ThinkPad-specific MCP tool behavior can be tested with synthetic manifest-backed records and without live DashScope calls.
- Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

- Result: Passed, 55 tests.
- M5 coverage added:
  - `ThinkPadToolService` lists supported models from a synthetic manifest.
  - `resolve_thinkpad_model` returns clarification for ambiguous `X1 Carbon battery removal`.
  - Machine type `21CB` resolves to the X1 Carbon Gen 10 / X1 Yoga Gen 7 manual candidate.
  - `lookup_error_code` returns a structured error-code row with citation.
  - `get_screw_spec` returns existing row fields and does not infer missing torque/count values.
  - `get_fru_procedure` requires an unambiguous model before returning procedure candidates.
  - `get_related_diagram` returns metadata only when `include_images=true`; image bytes remain out of M5 scope.
  - `get_safety_warnings` returns cited warning records.
  - MCP handlers return JSON `CallToolResult` content and invalid params do not expose tracebacks.
- Decision: M5 tool contracts are testable without copyrighted fixtures or provider credentials.

## M5-002: MCP Server Registration And Stdio Smoke

- Date: 2026-06-10
- Hypothesis: Adding ThinkPad-specific tools to default registration does not break the upstream MCP stdio server.
- Commands:

```powershell
.\.venv\Scripts\python -m pytest tests\integration\test_mcp_server.py -q
.\.venv\Scripts\python -m pytest tests\e2e\test_mcp_client.py -q
```

- Result:
  - Integration: passed, 6 tests; existing unknown `image` marker warnings remain.
  - E2E: passed, 7 tests.
- Failure note: The first E2E run failed in `test_multiple_tool_calls_same_session` after the test used `query_knowledge_hub` as one of several sequential calls. With M4 config defaulting to DashScope and no live key set, the query tool returned a provider-key error and the third response was not collected within the timeout. The test was corrected to use lightweight tool calls for the multi-call protocol scenario: `list_collections`, `resolve_thinkpad_model`, and `list_supported_models`.
- Decision: Default MCP startup and tools/list now include M5 ThinkPad tools, while live retrieval remains opt-in.

## M5-003: M5 Lint And Smoke Imports

- Date: 2026-06-10
- Hypothesis: M5-owned ThinkPad and MCP tool code passes the project lint scope and upstream smoke imports.
- Commands:

```powershell
.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py
.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q
```

- Result:
  - Ruff: passed.
  - Smoke imports: passed, 22 tests.
- Note: An extra e2e-inclusive ruff command failed on pre-existing pyupgrade findings in `tests/e2e/test_mcp_client.py` (`typing.Dict/List/Optional`). The planned M5 lint scope passed and the e2e test itself passed.
- Decision: M5 did not add new import or lint regressions in the ThinkPad/MCP tool scope.

## M5-004: Live Retrieval Status

- Date: 2026-06-10
- Status: Not run by default.
- Reason: `query_thinkpad_service` uses M4 retrieval and may require a local vector/BM25 index plus `DASHSCOPE_API_KEY`. M5 validates tool contracts and exact structured lookups without spending provider calls.
- Pending validation:

```powershell
$env:DASHSCOPE_API_KEY = "<set in local shell only>"
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --limit 50
```

- Decision: Keep live retrieval opt-in and record outputs under ignored local artifacts.

## M5-005: Live DashScope Provider Smoke

- Date: 2026-06-10
- Hypothesis: The configured DashScope providers work against the real API with the local environment variable set.
- Credential handling: `DASHSCOPE_API_KEY` was set only in the shell process. The key was not written to repository files.
- Command shape:

```powershell
$env:DASHSCOPE_API_KEY = "<local only>"
.\.venv\Scripts\python - <<'PY'
# create DashScope embedding, reranker, and LLM providers; send minimal requests
PY
```

- Result: Passed.
- Observed:
  - `text-embedding-v4` returned 1 embedding with dimension 1024.
  - `qwen3-rerank` ranked the battery candidate first for query `battery removal`.
  - `qwen3.5-flash` returned `OK` for a one-token style smoke prompt.
- Decision: Provider credentials, endpoints, payloads, and response parsing work in live mode.

## M5-006: Live Retrieval Index Hardening

- Date: 2026-06-10
- Hypothesis: M3 artifacts can be embedded into a local live `thinkpad_m4` index with DashScope.
- Initial command:

```powershell
$env:DASHSCOPE_API_KEY = "<local only>"
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m5_live_smoke --limit 50 --force-clear
```

- First result: Failed. DashScope rejected the old default batch size of 50 and reported the request batch size must not exceed 20.
- Second result after setting batch size 20: Failed. DashScope rejected this request shape and reported the request batch size must not exceed 10.
- Fix:
  - `DashScopeEmbedding.max_batch_size` is now 10.
  - `scripts/thinkpad_build_retrieval_index.py` defaults to `--batch-size 10`.
  - `build_thinkpad_retrieval_index()` caps requested batch size to provider `max_batch_size`.
  - Added a synthetic regression test proving provider max batch size is respected.
- Small live index after fix: Passed.
- Small live metrics:

```json
{
  "batch_size_used": 10,
  "bm25_doc_count": 50,
  "chunk_count": 50,
  "collection": "thinkpad_m5_live_smoke",
  "dry_run": false,
  "embedded_count": 50,
  "vector_count": 50
}
```

- Full live command:

```powershell
$env:DASHSCOPE_API_KEY = "<local only>"
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --force-clear
```

- First full result: Failed after about 222 seconds with a transient remote connection reset.
- Fix: `DashScopeEmbedding` now retries transient request errors and retryable 429/5xx responses with short exponential backoff.
- Final full result: Passed in about 416 seconds.
- Full live metrics:

```json
{
  "batch_size_used": 10,
  "bm25_doc_count": 2964,
  "chunk_count": 2964,
  "collection": "thinkpad_m4",
  "dry_run": false,
  "embedded_count": 2964,
  "vector_count": 2964
}
```

- Decision: Full local live index is now built under ignored `data/db` paths. M6 can use it for golden retrieval evaluation.

## M5-007: Live Retrieval And MCP Query Smoke

- Date: 2026-06-10
- Hypothesis: The live `thinkpad_m4` index can support model-aware retrieval and M5 MCP tool wrapping.
- Commands:

```powershell
$env:DASHSCOPE_API_KEY = "<local only>"
# Call retrieve_thinkpad(...) for representative queries and summarize top metadata only.
# Call query_thinkpad_service_handler(...) for one MCP tool smoke.
```

- Result: Passed.
- Query observations:
  - `X1 Carbon battery removal`: returned `clarification_needed=True`, `reason=generation_required`, 0 results.
  - `X1 Carbon Gen 9 battery removal`: returned 3 results, all from `thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm`.
  - `21CB battery removal`: returned 3 results, all from `thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm`.
  - `error code 0271`: returned structured table evidence from HMM table records.
  - `battery safety warning`: returned warning evidence records.
  - MCP `query_thinkpad_service` for `21CB battery removal`: returned `status=ok`, `isError=False`, 2 results, both from the expected Gen10 manual.
- Additional bug found and fixed:
  - Before the fix, a resolved model query could return wrong-manual results if the indexed sample did not contain any allowed manual hits.
  - `_filter_wrong_manuals()` now hard-filters resolved model results and returns empty evidence instead of falling back to wrong manuals.
  - Added a regression test for the no-allowed-manual case.
- Retrieval quality note:
  - Battery-removal queries currently rank safety-warning evidence above FRU procedure evidence in some cases. This is acceptable for smoke but should become an M6 golden-set/rerank tuning item.
- Decision: Live retrieval is functional and model-aware, but answer quality and ranking metrics still need M6 evaluation.

## M5-008: Live-Fix Regression Validation

- Date: 2026-06-10
- Hypothesis: The live-discovered batch-size, retry, and wrong-manual filtering fixes remain covered by deterministic local tests.
- Commands and results:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Passed, 57 tests |
| `.\.venv\Scripts\python -m pytest tests\unit\test_dashscope_providers.py -q` | Passed, 6 tests |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Passed, 22 tests |
| `.\.venv\Scripts\python -m pytest tests\integration\test_mcp_server.py -q` | Passed, 6 tests; existing unknown `image` marker warnings remain |
| `.\.venv\Scripts\ruff check src\libs\embedding\dashscope_embedding.py src\thinkpad\retrieval.py src\thinkpad\retrieval_index.py scripts\thinkpad_build_retrieval_index.py tests\thinkpad\test_retrieval.py tests\thinkpad\test_retrieval_corpus.py tests\unit\test_dashscope_providers.py` | Passed |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Passed |
| `git diff --check` | Passed; Git printed Windows CRLF conversion warnings only |

- Decision: The live fixes have deterministic regression coverage and do not require live provider calls in default test runs.

## M6-001: ThinkPad Golden Set And Evaluator Unit Tests

- Date: 2026-06-12
- Hypothesis: ThinkPad tool evidence needs a domain-specific golden set and evaluator rather than upstream chunk-id-only evaluation.
- Golden set: `tests/fixtures/thinkpad_m6_golden_set.json`
- Case count: 30
- Coverage:
  - model ambiguity
  - machine type resolution
  - error code lookup
  - screw and torque lookup
  - FRU procedure lookup
  - diagram metadata lookup
  - safety warning lookup
  - negative and unsupported queries
  - live retrieval smoke

Command:

```powershell
New-Item -ItemType Directory -Force -Path .pytest_tmp | Out-Null
$env:TEMP=(Resolve-Path .pytest_tmp)
$env:TMP=$env:TEMP
.\.venv\Scripts\python -m pytest tests\thinkpad\test_evaluation.py -q
```

Result: Passed, 9 tests.

Decision: M6 evaluator tests use synthetic service responses and do not require Lenovo PDFs or provider credentials.

## M6-002: Structured Tool Evaluation Baseline

- Date: 2026-06-12
- Hypothesis: The M6 evaluator can score structured M5 evidence tools without live provider calls.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m6_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --top-k 5 `
  --output data\eval\m6_report_structured.json
```

Result: Passed and wrote an ignored local report.

Structured metrics:

| Metric | Value |
|---|---:|
| Query count | 30 |
| Evaluated cases | 26 |
| Skipped live retrieval cases | 4 |
| Failed evaluated cases | 1 |
| `tool_status_accuracy` | 0.9615 |
| `manual_hit_at_k` | 0.9444 |
| `manual_mrr` | 0.9000 |
| `record_type_hit_at_k` | 0.9231 |
| `citation_accuracy` | 0.9231 |

Failure:

- `m6_screw_t480_exact_size` expected an exact screw table hit for `M2 x 3` but returned `not_found`.
- Cause: current exact matching does not normalize ASCII `x` to PDF-extracted multiplication sign `×`.

Decision: Keep this failed case as a real baseline finding rather than weakening the golden set.

## M6-003: Live Retrieval Evaluation Baseline

- Date: 2026-06-12
- Hypothesis: The live `thinkpad_m4` index can pass the M6 retrieval smoke cases through `query_thinkpad_service`.
- Credential handling: `DASHSCOPE_API_KEY` was supplied only through the shell process and was not written to files.

Command:

```powershell
$env:DASHSCOPE_API_KEY = "<local only>"
.\.venv\Scripts\python scripts\thinkpad_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m6_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --top-k 5 `
  --require-live-retrieval `
  --output data\eval\m6_report.json
```

Result: Passed and wrote an ignored local report.

Live metrics:

| Metric | Value |
|---|---:|
| Query count | 30 |
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

Live retrieval category:

- 4 live retrieval cases evaluated.
- `manual_hit_at_k=1.0`
- `manual_mrr=1.0`
- `record_type_hit_at_k=1.0`
- `citation_accuracy=1.0`

Decision: Live retrieval is now measured as a baseline, but M6 still does not evaluate generated repair answers.

## M6-004: Lightweight Dashboard Report Viewer

- Date: 2026-06-12
- Hypothesis: M6 can add dashboard visibility without triggering provider calls or index writes from the UI.
- Implementation behavior:
  - The ThinkPad Evaluation page reads `data/eval/m6_report.json` by default.
  - Missing report is handled as an informational empty state.
  - Synthetic report rendering is covered by smoke tests.
  - The page is read-only and does not run evaluation.

Command:

```powershell
New-Item -ItemType Directory -Force -Path .pytest_tmp | Out-Null
$env:TEMP=(Resolve-Path .pytest_tmp)
$env:TMP=$env:TEMP
.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q
```

Result: Passed, 8 tests.

Decision: Dashboard work stays intentionally lightweight; evaluation truth remains in the CLI JSON report and `docs/EVAL_REPORT.md`.

## M6-005: Final Local Validation

- Date: 2026-06-12
- Hypothesis: M6 changes preserve existing ThinkPad tests, smoke imports, dashboard smoke, lint, and whitespace checks.
- Note: pytest commands set `TEMP` and `TMP` to `.pytest_tmp` because the default Windows pytest temp root returned `WinError 5` in this session.

Commands and results:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Passed, 66 tests |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Passed, 22 tests |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Passed, 8 tests |
| `.\.venv\Scripts\ruff check src\thinkpad scripts\thinkpad_*.py tests\thinkpad src\observability\dashboard\pages\thinkpad_evaluation.py tests\e2e\test_dashboard_smoke.py` | Passed |
| `git diff --check` | Passed; Git printed Windows CRLF conversion warnings only |

Decision: M6 is ready for milestone commit after staging only tracked implementation/docs/test files and excluding local `data/`, drafts, interviews, and private interview notes.
