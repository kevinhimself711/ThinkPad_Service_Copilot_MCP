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

## M6.1-001: Push M6 Commit

- Date: 2026-06-12
- Hypothesis: Network access is restored and the local M6 milestone commit can be synchronized before applying the remediation fix.

Command:

```powershell
git push origin thinkpad-hmm-domain
git status -sb
git log --oneline --decorate -3
```

Result: Passed. Remote `origin/thinkpad-hmm-domain` now contains `1597bef test(thinkpad): add M6 evaluation baseline`.

Decision: M6.1 can be committed as a separate remediation commit on top of M6 instead of mixing the M6 baseline and the fix.

## M6.1-002: Screw-Spec Normalization Unit Coverage

- Date: 2026-06-12
- Hypothesis: Screw-size exact lookup should treat common multiplication forms as equivalent without weakening error-code exact matching.

Code behavior tested:

- `M2 x 3` matches extracted `M2 × 3 mm`.
- `M2*3` matches extracted `M2 × 3 mm`.
- `M2x3 mm` matches extracted `M2 × 3 mm`.
- `0271` still matches as an exact error code.
- `271` does not match embedded inside `0271`.

Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad\test_tool_service.py tests\thinkpad\test_evaluation.py -q
.\.venv\Scripts\ruff check src\thinkpad\tool_service.py tests\thinkpad\test_tool_service.py
```

Result: Passed; 19 tests and focused lint passed.

Decision: Keep screw-size normalization in the generic structured lookup helper while leaving exact-code matching isolated.

## M6.1-003: Structured Golden Set Regression

- Date: 2026-06-12
- Hypothesis: Re-running the same M6 golden set after normalization should remove the single screw-spec failure without changing the fixture.

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
| Failed evaluated cases | 0 |
| `tool_status_accuracy` | 1.0000 |
| `manual_hit_at_k` | 1.0000 |
| `manual_mrr` | 0.9556 |
| `record_type_hit_at_k` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `identifier_hit_at_k` | 1.0000 |

Decision: The M6 failure was a lookup-normalization issue, not a bad golden expectation.

## M6.1-004: Live Golden Set Regression

- Date: 2026-06-12
- Hypothesis: The same remediation should also close the live M6 evaluation failure while keeping live retrieval cases measured.
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
| Failed cases | 0 |
| Passed case rate | 1.0000 |
| `tool_status_accuracy` | 1.0000 |
| `manual_hit_at_k` | 1.0000 |
| `manual_mrr` | 0.9600 |
| `record_type_hit_at_k` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `identifier_hit_at_k` | 1.0000 |
| `latency_ms_p95` | 6268.05 |

Decision: M6.1 produces a clean live M6 regression result. The latency p95 remains provider/runtime-sensitive and is recorded separately from retrieval quality.

## M6.1-005: Final Local Validation

- Date: 2026-06-12
- Hypothesis: The remediation preserves the broader ThinkPad, upstream smoke, dashboard, lint, and whitespace checks.
- Note: pytest commands set `TEMP` and `TMP` to `.pytest_tmp` because the default Windows pytest temp root returned `WinError 5` earlier in this project session.

Commands and results:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Passed, 68 tests |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Passed, 22 tests |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Passed, 8 tests |
| `.\.venv\Scripts\ruff check src\thinkpad scripts\thinkpad_*.py tests\thinkpad src\observability\dashboard\pages\thinkpad_evaluation.py tests\e2e\test_dashboard_smoke.py` | Passed |
| `git diff --check` | Passed; Git printed Windows CRLF conversion warnings only |
| Working diff secret scan for provider-key patterns | Passed |

Decision: M6.1 is ready for a remediation commit after staging only tracked implementation/docs/test files and excluding local `data/`, drafts, interviews, and private interview notes.

## M7-001: FRU Graph Unit And Tool Tests

- Date: 2026-06-12
- Hypothesis: M3 FRU procedures and dependency edges can be converted into a deterministic in-memory graph without adding a graph database or third-party dependency.

Code behavior tested:

- Direct prerequisite chain preserves node citation.
- Multi-hop chain returns deterministic depth ordering.
- Missing prerequisite nodes are reported.
- Cycles terminate and set `cycle_detected=true`.
- `get_fru_dependency_chain` requires an unambiguous model.
- MCP registration and handler return JSON graph evidence.
- Evaluator supports `get_fru_dependency_chain` without injecting `top_k`.

Command:

```powershell
.\.venv\Scripts\python -m pytest `
  tests\thinkpad\test_fru_graph.py `
  tests\thinkpad\test_tool_service.py `
  tests\thinkpad\test_thinkpad_mcp_tools.py `
  tests\thinkpad\test_evaluation.py -q
```

Result: Passed, 34 tests.

Decision: Keep M7 graph traversal standard-library only and reuse the existing ThinkPad service/MCP response envelope.

## M7-002: Structured Graph Golden Evaluation

- Date: 2026-06-12
- Hypothesis: A M7 golden set can preserve all M6 cases and add graph traversal cases without live retrieval as a default requirement.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m7_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --top-k 5 `
  --output data\eval\m7_report_structured.json
```

Result: Passed and wrote an ignored local report.

Structured metrics:

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

Graph category:

- 4 graph `ok` cases evaluated.
- 1 graph ambiguity case evaluated.
- 1 graph negative case evaluated.
- 0 graph failures.

Decision: M7 graph evidence is measurable and can be carried into M8 agent planning as a tool, not as final repair prose.

## M7-003: Final Local Validation

- Date: 2026-06-12
- Hypothesis: M7 graph changes preserve ThinkPad tests, upstream smoke imports, dashboard smoke, lint, whitespace checks, and provider-secret hygiene.
- Note: pytest commands set `TEMP` and `TMP` to `.pytest_tmp` because the default Windows pytest temp root returned `WinError 5` earlier in this project session.

Commands and results:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Passed, 78 tests |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Passed, 22 tests |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Passed, 8 tests |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Passed |
| `git diff --check` | Passed; Git printed Windows CRLF conversion warnings only |
| Working diff secret scan for provider-key patterns | Passed |

Decision: M7 is ready for milestone commit after staging only tracked implementation/docs/test files plus new graph module, M7 fixture, and graph tests; local `data/`, drafts, interviews, and private interview notes stay uncommitted.

## M7.1-001: Pre-M8 Milestone Audit Fact Collection

- Date: 2026-06-12
- Hypothesis: M0-M7 completion can be audited from committed docs/code/tests plus ignored local evaluation artifacts without mutating product behavior or downloading new manuals.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_audit_milestones.py `
  --output data\eval\m0_m7_audit.json
```

Result: Passed and wrote ignored local audit JSON.

Collected facts:

| Fact | Value |
|---|---:|
| Branch | `thinkpad-hmm-domain` |
| Head before M7.1 commit | `70154ea feat(thinkpad): add FRU dependency graph tool` |
| M3 manuals succeeded | 8 |
| M3 pages | 877 |
| M3 tables | 797 |
| M3 figures | 1285 |
| M3 FRU procedures | 195 |
| M3 dependency edges | 535 |
| M3 warnings | 687 |
| M6 golden cases | 30 |
| M7 golden cases | 36 |

Decision: Add `docs/M0_M7_PROGRESS_AUDIT.md` as the canonical human-readable report and keep `data/eval/m0_m7_audit.json` ignored.

## M7.1-002: Structured Regression Before M8

- Date: 2026-06-12
- Hypothesis: Current M7 graph work and M6.1 remediation still pass the default structured regression suite before M8 starts.

Commands and results:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | Initial run hit `WinError 5` on the default Windows pytest temp root before test bodies. |
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q --basetemp data\tmp\pytest` | Passed, 78 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Passed, 22 tests. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Passed, 8 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Passed. |

M7 structured evaluation command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m7_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --top-k 5 `
  --output data\eval\m7_report_structured.json
```

Structured result:

| Metric | Value |
|---|---:|
| Query count | 36 |
| Evaluated cases | 32 |
| Skipped live retrieval cases | 4 |
| Failed evaluated cases | 0 |
| `tool_status_accuracy` | 1.0000 |
| `manual_hit_at_k` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `identifier_hit_at_k` | 1.0000 |

Decision: Structured behavior is clean enough for M8 planning. The pytest temp-root issue is environmental; using an ignored basetemp is the local workaround.

## M7.1-003: Live DashScope Regression Before M8

- Date: 2026-06-12
- Hypothesis: The current local `thinkpad_m4` index and DashScope provider path still support live retrieval cases in the M7 golden set.
- Credential handling: `DASHSCOPE_API_KEY` was set only in the local shell process for the command and was not written to files.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m7_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --top-k 5 `
  --require-live-retrieval `
  --output data\eval\m7_report_live.json
```

Result: Passed and wrote ignored local live report.

Live metrics:

| Metric | Value |
|---|---:|
| Query count | 36 |
| Evaluated cases | 36 |
| Skipped cases | 0 |
| Failed cases | 0 |
| `tool_status_accuracy` | 1.0000 |
| `manual_hit_at_k` | 1.0000 |
| `manual_mrr` | 0.9667 |
| `record_type_hit_at_k` | 1.0000 |
| `record_type_mrr` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `identifier_hit_at_k` | 1.0000 |
| `latency_ms_p95` | 5339.75 |

Decision: Do not rebuild the full live index in M7.1. The existing ignored local index is present and the live regression passes. A full rebuild would add provider cost without changing the pre-M8 readiness decision.

## M7.1-004: M0-M7 Audit Verdict

- Date: 2026-06-12
- Hypothesis: M8 can start if M0-M7 have explicit evidence, known risks, and no unrecorded blockers.

Result: `docs/M0_M7_PROGRESS_AUDIT.md` records:

- M0, M2, M5, M6, and M6.1 as `complete`.
- M1, M3, M4, and M7 as `complete_with_risk`.
- M8 Agent Client, answer faithfulness evaluation, broader golden sets, full human extraction audit, and production packaging as deferred.

Decision: M8 can proceed after the M7.1 audit docs and script are committed. The next phase must evaluate generated repair plans separately and must not treat M7 graph evidence metrics as answer-quality metrics.

## M8-001: Agent Unit And Evaluator Contract Tests

- Date: 2026-06-12
- Hypothesis: A deterministic repair-planning agent can orchestrate existing evidence tools without exposing a new MCP tool, and the evaluator can score trajectory, citation, safety, provider, and unsupported-claim behavior.

Commands and results:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_agent.py tests\thinkpad\test_agent_evaluation.py -q --basetemp data\tmp\pytest_m8_agent` | Passed, 9 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad\agent.py src\thinkpad\agent_evaluation.py tests\thinkpad\test_agent.py tests\thinkpad\test_agent_evaluation.py scripts\thinkpad_agent_*.py` | Passed. |

Validated behaviors:

- Ambiguous model query returns `clarification_required`.
- Machine-type query produces resolver, FRU procedure, dependency-chain, diagram, and safety tool trajectory.
- Screw lookup is called only for screw/spec evidence queries.
- Unsupported specific model returns refusal/not-found without LLM call.
- Fake LLM output with unsupported identifiers is marked by validation.
- Evaluator records provider errors, forbidden-tool failures, citation checks, safety inclusion, and trajectory coverage.

Decision: proceed to full 96-case deterministic agent evaluation.

## M8-002: Deterministic 96-Case Agent Golden Baseline

- Date: 2026-06-12
- Hypothesis: The no-LLM agent path should pass the full committed M8 golden set before live retrieval or live LLM is evaluated.
- Golden set: `tests/fixtures/thinkpad_m8_agent_golden_set.json`
- Cases: 96

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --mode deterministic `
  --output data\eval\m8_agent_report_deterministic.json `
  --progress-jsonl data\eval\m8_agent_progress_deterministic.jsonl
```

Result: Passed and wrote ignored local report.

| Metric | Value |
|---|---:|
| Cases | 96 |
| Failed cases | 0 |
| `passed_case_rate` | 1.0000 |
| `final_plan_status_accuracy` | 1.0000 |
| `trajectory_tool_sequence_accuracy` | 1.0000 |
| `required_tool_coverage` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `evidence_identifier_coverage` | 1.0000 |
| `safety_warning_inclusion` | 1.0000 |
| `unsupported_claim_rate` | 0.0000 |
| `latency_ms_p95` | 16.00 |

Decision: deterministic orchestration is clean for the committed M8 golden set. This result should not be described as generated-answer quality.

## M8-003: Live DashScope Retrieval 96-Case Agent Baseline

- Date: 2026-06-12
- Hypothesis: Full M8 agent evaluation can run against the live DashScope retrieval path at 96-case scale without silent skips.
- Credential handling: `DASHSCOPE_API_KEY` was set only in the local shell process and was not written to files.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --require-live-retrieval `
  --output data\eval\m8_agent_report_live_retrieval.json `
  --progress-jsonl data\eval\m8_agent_progress_live_retrieval.jsonl
```

Result: Passed and wrote ignored local report. Runtime was about 2 minutes 52 seconds.

Observed live behavior:

- 4 DashScope rerank connection resets were recorded.
- The agent fell back to deterministic fused/domain-ranked retrieval evidence.
- No case failed.

| Metric | Value |
|---|---:|
| Cases | 96 |
| Failed cases | 0 |
| `passed_case_rate` | 1.0000 |
| `provider_error_rate` | 0.0000 |
| `retrieval_fallback_rate` | 0.0417 |
| `unsupported_claim_rate` | 0.0000 |
| `citation_accuracy` | 1.0000 |
| `latency_ms_p50` | 1344.00 |
| `latency_ms_p95` | 6032.00 |

Decision: live retrieval is usable for M8 agent evaluation, and the fallback behavior is visible. Do not hide fallback rate behind a headline pass rate.

## M8-004: Live DashScope LLM 96-Case Agent Baseline

- Date: 2026-06-12
- Hypothesis: Live DashScope LLM composition can rewrite retrieved evidence into cited repair plans, but generated plan faithfulness must be measured separately from evidence retrieval.
- Model behavior: LLM composition was enabled only for cases marked `llm_required=true`; all 96 cases were still evaluated.
- Credential handling: `DASHSCOPE_API_KEY` was set only in the local shell process and was not written to files.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --live-llm `
  --output data\eval\m8_agent_report_live_llm.json `
  --progress-jsonl data\eval\m8_agent_progress_live_llm.jsonl
```

Result: Completed and wrote ignored local report. Runtime was about 32 minutes 19 seconds.

Observed live behavior:

- Multiple DashScope rerank connection resets occurred and fell back to deterministic evidence.
- One dense retrieval embedding connection reset fell back to sparse-only evidence.
- 5 cases failed, all in live LLM/provider composition or validation.

| Metric | Value |
|---|---:|
| Cases | 96 |
| LLM-required cases | 36 |
| Failed cases | 5 |
| `passed_case_rate` | 0.9479 |
| `final_plan_status_accuracy` | 0.9479 |
| `trajectory_tool_sequence_accuracy` | 1.0000 |
| `required_tool_coverage` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `llm_citation_preservation` | 0.8611 |
| `provider_error_rate` | 0.0521 |
| `retrieval_fallback_rate` | 0.0833 |
| `unsupported_claim_rate` | 0.0521 |
| `latency_ms_p50` | 4359.00 |
| `latency_ms_p95` | 59000.00 |

Failed cases:

- `m8_fru_thinkpad_t480_hmm_1010`
- `m8_fru_thinkpad_t490_hmm_1020`
- `m8_fru_thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm_1030`
- `m8_fru_thinkpad_p1_gen4_x1_extreme_gen4_hmm_1010`
- `m8_chain_thinkpad_t480_hmm_1020`

Decision: live LLM plan generation is useful but not clean. M8 should commit this as a measured baseline with remediation, not tune the golden set downward.

## M8-005: Stress Candidate Generation And Stress Runs

- Date: 2026-06-12
- Hypothesis: A larger non-gold stress set can expose robustness and alias/candidate-quality issues that a curated golden set may miss.
- Stress output: ignored `data/eval/m8_agent_stress_candidates.json`
- Cases: 194
- Note: These cases are generated from M3 extraction artifacts and are not human-reviewed gold truth.

Candidate generation command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_generate_agent_eval_candidates.py `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --output data\eval\m8_agent_stress_candidates.json `
  --per-manual 32
```

Generated case mix:

| Category | Cases |
|---|---:|
| `stress_error_code` | 64 |
| `stress_fru_procedure` | 64 |
| `stress_screw_spec` | 50 |
| `stress_safety` | 8 |
| `stress_diagram` | 8 |

Deterministic stress command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set data\eval\m8_agent_stress_candidates.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --mode deterministic `
  --output data\eval\m8_agent_stress_report_deterministic.json `
  --progress-jsonl data\eval\m8_agent_stress_progress_deterministic.jsonl
```

Live retrieval stress command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set data\eval\m8_agent_stress_candidates.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --require-live-retrieval `
  --output data\eval\m8_agent_stress_report_live_retrieval.json `
  --progress-jsonl data\eval\m8_agent_stress_progress_live_retrieval.jsonl
```

Stress results:

| Run | Cases | Failed | Pass Rate | Retrieval Fallback Rate | Citation Accuracy | Identifier Coverage | p95 Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Deterministic stress | 194 | 17 | 0.9124 | 0.0000 | 0.9227 | 0.9086 | 16.00 |
| Live retrieval stress | 194 | 17 | 0.9124 | 0.0309 | 0.9794 | 0.9785 | 6047.00 |

Findings:

- Stress failures are mostly diagnostic pseudo-FRUs and component alias gaps.
- Live retrieval improved citation and identifier coverage among successful cases but did not solve noisy candidate generation.
- Stress results should drive remediation, not headline accuracy claims.

Decision: keep the 96-case set as canonical M8 gold and use stress results as an M8/M9 hardening queue.

## M8-006: Final Regression And Lint Validation

- Date: 2026-06-12
- Hypothesis: M8 agent code, benchmark code, fixtures, and documentation preserve the full ThinkPad regression suite, upstream smoke imports, dashboard smoke, lint, and whitespace hygiene.

Commands and results:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q --basetemp data\tmp\pytest_m8_final` | Passed, 87 tests. |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | Passed, 22 tests. |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q` | Passed, 8 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Passed. |

Decision: M8 implementation and docs are ready for final whitespace/secret checks and milestone commit. Local `data/eval/` reports, provider traces, vector/index artifacts, and private interview notes remain uncommitted.

## M8.1-001: Agent Composer Hardening Unit Tests

- Date: 2026-06-13
- Hypothesis: LLM composition failures can be separated into malformed output, missing citation, unsupported claim, provider error, and recovered provider error without weakening deterministic agent behavior.

Commands and results:

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad\test_agent.py tests\thinkpad\test_agent_evaluation.py -q --basetemp data\tmp\pytest_m8_1_focused3 -p no:cacheprovider` | Passed, 13 tests. |
| `.\.venv\Scripts\ruff check src\thinkpad\agent.py src\thinkpad\agent_evaluation.py scripts\thinkpad_agent_evaluate.py scripts\thinkpad_agent_plan.py scripts\thinkpad_generate_agent_eval_candidates.py tests\thinkpad\test_agent.py tests\thinkpad\test_agent_evaluation.py` | Passed. |

Decision: The local evidence normalizer may recover malformed/missing-citation/provider failures, but unsupported identifiers remain hard failures.

## M8.1-002: Deterministic And Stress Remediation Runs

- Date: 2026-06-13
- Hypothesis: M8.1 changes should preserve deterministic 96-case behavior and reduce stress candidate noise by filtering diagnostic pseudo-FRUs.

Commands:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --mode deterministic `
  --output data\eval\m8_1_agent_report_deterministic.json

.\.venv\Scripts\python scripts\thinkpad_generate_agent_eval_candidates.py `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --output data\eval\m8_1_agent_stress_candidates.json `
  --per-manual 32

.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set data\eval\m8_1_agent_stress_candidates.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --mode deterministic `
  --output data\eval\m8_1_agent_stress_report_deterministic.json
```

Results:

| Run | Cases | Failed | Pass Rate |
|---|---:|---:|---:|
| M8.1 deterministic gold | 96 | 0 | 1.0000 |
| M8.1 stress deterministic | 194 | 10 | 0.9485 |

Decision: deterministic gold behavior is preserved, and stress failures drop from 17 to 10 after pseudo-FRU filtering and alias cleanup.

## M8.1-003: Live Retrieval And Live LLM Validation

- Date: 2026-06-13
- Hypothesis: Unsandboxed DashScope live runs should preserve M8.1 golden-set correctness while recording provider fallback/error rates.
- Note: A sandboxed live LLM attempt produced many `WinError 10013` socket-permission failures and is not used as the valid live result. The accepted result below was run with network access enabled.

Commands:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --require-live-retrieval `
  --output data\eval\m8_1_agent_report_live_retrieval.json

.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --live-llm `
  --llm-repair-attempts 1 `
  --output data\eval\m8_1_agent_report_live_llm.json
```

Results:

| Run | Cases | Failed | Pass Rate | Provider Error Rate | Retrieval Fallback Rate | p95 Latency |
|---|---:|---:|---:|---:|---:|---:|
| M8.1 live retrieval gold | 96 | 0 | 1.0000 | 0.0000 | 0.1354 | 9140 ms |
| M8.1 live LLM gold | 96 | 0 | 1.0000 | 0.0104 | 0.0000 | 90015 ms |

Decision: M8.1 closes the M8 live LLM golden-set failure. Provider fallback/error rates remain visible and should be included in demo caveats.

## M8.1-004: Stress Live Retrieval

- Date: 2026-06-13
- Hypothesis: Live retrieval should not hide remaining stress FRU procedure failures after candidate cleanup.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set data\eval\m8_1_agent_stress_candidates.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --require-live-retrieval `
  --output data\eval\m8_1_agent_stress_report_live_retrieval.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 194 |
| Failed cases | 10 |
| `passed_case_rate` | 0.9485 |
| `citation_accuracy` | 0.9794 |
| `evidence_identifier_coverage` | 0.9731 |
| `retrieval_fallback_rate` | 0.0258 |

Remaining failures are clustered in USB board, wireless WAN/LAN, and power button / fingerprint reader procedure candidates. These remain non-gold stress findings.

## M8.2-001: Strict/Raw Evaluator Unit Tests

- Date: 2026-06-13
- Hypothesis: The evaluator can expose raw LLM failures and strict citation failures without changing M8.1 agent fallback behavior.

Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q --basetemp data\tmp\pytest_m8_2_focused2 -p no:cacheprovider
```

Result: passed, 95 tests.

Decision: normal mode can still recover provider failures with evidence-only fallback, while `strict_live_llm` and `strict_citation` preserve failures for evaluation.

## M8.2-002: Deterministic Strict Anti-Inflation Run

- Date: 2026-06-13
- Hypothesis: A stricter 120-case fixture and per-step citation scoring should prevent M8.1-style aggregate `1.0000` from being overinterpreted.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --mode deterministic `
  --strict-citation `
  --output data\eval\m8_2_report_deterministic_strict.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 120 |
| Failed cases | 74 |
| `passed_case_rate` | 0.3833 |
| `final_plan_status_accuracy` | 0.8833 |
| `citation_accuracy` | 0.8958 |
| `strict_citation_accuracy` | 0.2708 |
| `all_step_citation_coverage` | 0.9062 |

Decision: the previous 1.0 headline was contract-level. Strict citation and harder cases expose real measurement gaps.

## M8.2-003: Live Retrieval Strict Run

- Date: 2026-06-13
- Hypothesis: Live retrieval should remain operational, but strict citation should still keep the benchmark below inflated 1.0.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --require-live-retrieval `
  --strict-citation `
  --output data\eval\m8_2_report_live_retrieval_strict.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 120 |
| Failed cases | 73 |
| `passed_case_rate` | 0.3917 |
| `strict_citation_accuracy` | 0.3021 |
| `provider_error_rate` | 0.0000 |
| `retrieval_fallback_rate` | 0.0083 |
| `latency_ms_p95` | 1657 ms |

Decision: retrieval remains available and slightly improves some hard diagram/alias cases, but does not solve strict per-step citation issues.

## M8.2-004: Raw Live LLM Strict Run

- Date: 2026-06-13
- Hypothesis: disabling M8.1 evidence-only fallback will expose raw LLM/provider output quality separately from recovered user-visible success.
- Execution note: one full 120-case run exceeded the 20-minute command timeout. The accepted result was produced from six 20-case chunks and combined into `data\eval\m8_2_report_raw_live_llm_strict.json`.

Command shape:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --live-llm `
  --strict-live-llm `
  --strict-citation `
  --offset <0|20|40|60|80|100> `
  --limit 20 `
  --output data\eval\m8_2_report_raw_live_llm_strict_part_<offset>.json
```

Combined result:

| Metric | Value |
|---|---:|
| Cases | 120 |
| Failed cases | 82 |
| `passed_case_rate` | 0.3167 |
| `raw_llm_success_rate` | 0.0417 |
| `llm_citation_preservation` | 0.0833 |
| `fallback_recovered_rate` | 0.0000 |
| `provider_error_rate` | 0.0000 |
| `latency_ms_p95` | 52109 ms |

Decision: raw live LLM quality is much weaker than M8.1 recovered success. This is the correct metric to cite when discussing raw generation reliability.

## M8.2-005: Stress Live Retrieval Strict Run

- Date: 2026-06-13
- Hypothesis: strict citation scoring over generated stress cases should expose extraction/alias weaknesses even more clearly.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set data\eval\m8_1_agent_stress_candidates.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --require-live-retrieval `
  --strict-citation `
  --output data\eval\m8_2_stress_live_retrieval_strict.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 194 |
| Failed cases | 178 |
| `passed_case_rate` | 0.0825 |
| `final_plan_status_accuracy` | 0.9485 |
| `strict_citation_accuracy` | 0.1031 |
| `provider_error_rate` | 0.0000 |

Decision: stress failures remain non-gold pressure-test findings. The low strict pass rate should be used to prioritize alias and per-step citation schema work, not as a product accuracy number.

## M8.2-006: M3 Extraction Spot-Check

- Date: 2026-06-13
- Hypothesis: a small field-level check can verify that sampled M3 candidate records point to real pages and plausible page signals without committing copyrighted manual text.

Result:

| Metric | Value |
|---|---:|
| Manuals sampled | 8 |
| Records sampled | 24 |
| Pass | 24 |
| Review/fail | 0 |

Decision: sampled procedure/table/figure/warning records have valid page and record signals. This does not replace a full human audit of all extracted candidates.

## M8.3-001: Agent And Evaluator Remediation Tests

- Date: 2026-06-13
- Hypothesis: targeted changes can improve strict evaluation without weakening grounding rules.

Commands:

```powershell
$env:TEMP='D:\ThinkPad_Service_Copilot_MCP\data\tmp\sys_temp'; $env:TMP=$env:TEMP
.\.venv\Scripts\python -m pytest tests\thinkpad -q

$env:TEMP='D:\ThinkPad_Service_Copilot_MCP\data\tmp\sys_temp'; $env:TMP=$env:TEMP
.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q

$env:TEMP='D:\ThinkPad_Service_Copilot_MCP\data\tmp\sys_temp'; $env:TMP=$env:TEMP
.\.venv\Scripts\python -m pytest tests\e2e\test_dashboard_smoke.py -q

.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py
```

Results:

| Command | Result |
|---|---|
| `pytest tests\thinkpad -q` | Passed, 100 tests. |
| `pytest tests\unit\test_smoke_imports.py -q` | Passed, 22 tests. |
| `pytest tests\e2e\test_dashboard_smoke.py -q` | Passed, 8 tests. |
| `ruff check ...` | Passed. |

Execution note: the default Windows temp directory had a local permission issue, so pytest was run with `TEMP` and `TMP` pointed at ignored `data\tmp\sys_temp`.

## M8.3-002: Deterministic Strict Usability Run

- Date: 2026-06-13
- Hypothesis: revised strict citation semantics plus procedure-step planning should make the 120-case strict benchmark pass without hiding required evidence failures.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --strict-citation --output data\eval\m8_3_report_deterministic_strict.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 120 |
| Failed cases | 0 |
| `passed_case_rate` | 1.0000 |
| `final_plan_status_accuracy` | 1.0000 |
| `per_step_citation_validity` | 1.0000 |
| `required_record_type_coverage` | 1.0000 |
| `required_evidence_coverage` | 1.0000 |

Decision: M8.3 fixed the deterministic strict contract failures from M8.2. This is still a benchmark result, not open-world accuracy.

## M8.3-003: Live Retrieval Strict Usability Run

- Date: 2026-06-13
- Hypothesis: live retrieval should remain clean after the agent/evaluator changes and should not regress strict metrics.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --strict-citation --output data\eval\m8_3_report_live_retrieval_strict.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 120 |
| Failed cases | 0 |
| `passed_case_rate` | 1.0000 |
| `provider_error_rate` | 0.0000 |
| `retrieval_fallback_rate` | 0.0000 |
| `latency_ms_p95` | 1594 ms |

Decision: retrieval is not the current bottleneck for the M8.3 benchmark.

## M8.3-004: Raw Live LLM Strict Usability Run

- Date: 2026-06-13
- Hypothesis: compact cited plan input and stricter JSON composition should raise raw LLM quality without relying on fallback.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --live-llm --strict-live-llm --strict-citation --output data\eval\m8_3_report_raw_live_llm_strict.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 120 |
| Failed cases | 3 |
| `passed_case_rate` | 0.9750 |
| `raw_llm_success_rate` | 0.9375 |
| `llm_citation_preservation` | 0.9375 |
| `provider_error_rate` | 0.0250 |
| `unsupported_claim_rate` | 0.0000 |
| `strict_citation_accuracy` | 1.0000 |
| `latency_ms_p95` | 52187 ms |

Decision: raw LLM composition is much improved from M8.2, but provider timeout/error and latency are still real demo risks. Raw LLM-only planning should not be the default.

## M8.3-005: Stress Live Retrieval Strict Run

- Date: 2026-06-13
- Hypothesis: alias and plan-generation cleanup should reduce non-gold stress failures.

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set data\eval\m8_1_agent_stress_candidates.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --require-live-retrieval --strict-citation --output data\eval\m8_3_stress_live_retrieval_strict.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 194 |
| Failed cases | 6 |
| `passed_case_rate` | 0.9691 |
| `final_plan_status_accuracy` | 0.9691 |
| `required_record_type_coverage` | 0.9794 |
| `per_step_citation_validity` | 0.9794 |
| `provider_error_rate` | 0.0000 |

Decision: remaining stress failures are concentrated in generated FRU procedure applicability conflicts, especially X1 Carbon queries paired with Yoga-only pen procedure labels and WWAN availability mismatch. The stress set remains a pressure test, not gold truth.
