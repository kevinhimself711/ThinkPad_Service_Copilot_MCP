# Evaluation Report

> Current scope: M4 retrieval baseline. This file records reproducible evaluation status and gaps. It does not claim final answer quality.

## M4 Retrieval Baseline

- Date: 2026-06-10
- Milestone: M4 ThinkPad Retrieval + DashScope Provider Wiring
- Corpus input: local ignored M3 extraction artifacts under `data/extracted/m3/`
- Evaluation type: synthetic retrieval guardrails plus local corpus dry-run
- Not evaluated yet: generated repair answers, MCP tool responses, live embedding recall, live rerank quality, FRU graph traversal, dashboard traces

### Baseline Artifacts

M3 extraction produced the local candidate pool:

| Artifact | Local path | M3 count |
|---|---|---:|
| Table records | `data/extracted/m3/tables.jsonl` | 797 |
| Figure records | `data/extracted/m3/figures.jsonl` | 1285 |
| FRU procedures | `data/extracted/m3/fru_procedures.jsonl` | 195 |
| Warning records | `data/extracted/m3/warnings.jsonl` | 687 |
| Dependency edges | `data/extracted/m3/dependency_edges.jsonl` | 535 |

M4 corpus dry-run converted the searchable record types into 2964 retrieval chunks:

```powershell
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --dry-run
```

Result:

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

Because this was dry-run, `bm25_doc_count`, `embedded_count`, and `vector_count` are expected to be zero.

### Synthetic Retrieval Checks

Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

Result: passed, 42 tests.

M4-specific assertions:

- Ambiguous high-risk query `X1 Carbon battery removal` returns `clarification_needed=True`.
- Resolved query `X1 Carbon Gen 9 battery removal` filters wrong-generation manual results.
- Domain rerank boosts exact machine type/manual matches.
- Exact error-code query boosts structured error-code table records.
- Procedure queries boost `fru_procedure` records.
- Warning/safety queries boost `warning` records.
- Cited records are preferred over uncited records.

### Provider Checks

Command:

```powershell
.\.venv\Scripts\python -m pytest tests\unit\test_dashscope_providers.py -q
```

Result: passed, 5 tests.

Provider tests use mocked HTTP and do not require live credentials. They validate payload shape, response parsing, factory registration, and missing-key errors for:

- `text-embedding-v4`
- `qwen3-rerank`
- `qwen3.5-flash`

### Current Metrics

| Metric | Status |
|---|---|
| Chunk build count | 2964 dry-run chunks |
| Hit@K | Not measured yet |
| MRR | Not measured yet |
| Citation accuracy | Guardrail-tested synthetically, not measured on a golden set |
| Model/generation accuracy | Resolver unit-tested, not measured on full query set |
| Safety-warning recall | Rerank boost tested synthetically, not measured on golden set |
| Live rerank quality | Not run |
| Answer faithfulness | Out of M4 scope |

### Planned M4 Live Evaluation

Run only after explicitly setting `DASHSCOPE_API_KEY` in the local shell:

```powershell
$env:DASHSCOPE_API_KEY = "<set in local shell only>"
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --limit 50
```

Then run representative JSON retrieval queries:

```powershell
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "X1 Carbon battery removal" --collection thinkpad_m4
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "X1 Carbon Gen 9 battery removal" --collection thinkpad_m4
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "21CB battery removal" --collection thinkpad_m4
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "error code 0271" --collection thinkpad_m4
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "battery safety warning" --collection thinkpad_m4
```

Live query outputs should be stored under ignored local evaluation artifacts, not committed.

### Interpretation

M4 proves that the project now has:

- Provider wiring for DashScope embedding, rerank, and LLM calls.
- A citation-backed local retrieval corpus over M3 structured artifacts.
- A local index builder with dry-run mode.
- A retrieval facade that enforces model clarification and domain rerank guardrails.

M4 does not prove final answer correctness. M5 should add MCP tool contracts only after live index validation and a small golden retrieval set are recorded.

## M5 MCP Tool Contract Baseline

- Date: 2026-06-10
- Milestone: M5 ThinkPad-Specific MCP Tools
- Evaluation type: tool contract, schema, handler, and protocol smoke
- Not evaluated yet: final repair answer faithfulness, live embedding Hit@K/MRR, Graph RAG dependency traversal, agent tool-call trajectories

### Tools Exposed

M5 registers these ThinkPad-specific MCP tools:

| Tool | Evaluation status |
|---|---|
| `list_supported_models` | Synthetic service test and MCP registration test passed |
| `resolve_thinkpad_model` | Ambiguity and machine-type tests passed |
| `query_thinkpad_service` | Handler contract exists; live retrieval not run by default |
| `lookup_error_code` | Synthetic structured row lookup passed |
| `get_fru_procedure` | Ambiguity guard and structured candidate test passed |
| `get_screw_spec` | Structured row lookup passed; missing torque is not inferred |
| `get_related_diagram` | Metadata-only behavior passed |
| `get_safety_warnings` | Cited warning lookup passed |

### Test Results

| Command | Result |
|---|---|
| `.\.venv\Scripts\python -m pytest tests\thinkpad -q` | 55 passed |
| `.\.venv\Scripts\python -m pytest tests\integration\test_mcp_server.py -q` | 6 passed, 4 existing marker warnings |
| `.\.venv\Scripts\python -m pytest tests\e2e\test_mcp_client.py -q` | 7 passed |
| `.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q` | 22 passed |
| `.\.venv\Scripts\ruff check src\thinkpad src\mcp_server\tools\thinkpad_tools.py tests\thinkpad scripts\thinkpad_*.py` | Passed |

### Current Metrics

| Metric | Status |
|---|---|
| MCP tool registration | 8 ThinkPad tools registered |
| Tool response schema | Standard JSON envelope tested |
| Ambiguous model handling | Synthetic tests passed |
| Exact error-code lookup | Synthetic table-row test passed |
| Screw-spec non-inference | Synthetic table-row test passed |
| Diagram bytes | Not returned in M5 |
| Live retrieval quality | Not measured |
| Answer faithfulness | Out of M5 scope |

### Interpretation

M5 proves that ThinkPad-specific evidence tools are callable over the existing MCP server and preserve JSON citations. It does not prove that live retrieval quality is good, nor that generated repair answers are correct. M6 should turn these tool contracts into measured retrieval/evaluation scenarios before M7 graph traversal or M8 agent workflows.

## M5 Live DashScope Validation Addendum

- Date: 2026-06-10
- Validation type: paid live-provider smoke and full local indexing run
- Credential handling: `DASHSCOPE_API_KEY` was supplied only through the local shell environment and was not written to repository files.
- Collection validated: `thinkpad_m4`
- Data source: ignored local M3 extraction artifacts under `data/extracted/m3`

### Live Results

| Check | Result |
|---|---|
| DashScope embedding smoke | Passed; `text-embedding-v4` returned a 1024-dimension vector |
| DashScope rerank smoke | Passed; `qwen3-rerank` ranked the battery candidate first |
| DashScope LLM smoke | Passed; `qwen3.5-flash` returned a minimal response |
| Small live index | Passed with 50 chunks after reducing batch size to 10 |
| Full live index | Passed with 2964 chunks, 2964 embedded records, 2964 vector records, and 2964 BM25 docs |
| MCP `query_thinkpad_service` live smoke | Passed for `21CB battery removal`, returning expected Gen10 manual evidence |

### Issues Found

| Issue | Fix |
|---|---|
| DashScope rejected embedding batches larger than 10 for this request shape | Set DashScope embedding `max_batch_size=10`, changed the index CLI default to 10, and capped requested batch size by provider capability |
| Full live indexing hit a transient connection reset after several minutes | Added retry handling for transient request errors and retryable 429/5xx responses |
| Resolved model queries could fall back to wrong-manual hits when a limited index had no allowed manual records | Changed wrong-manual filtering to return empty evidence instead of falling back to wrong manuals |

### Current Quality Interpretation

This live run proves that M4/M5 retrieval infrastructure can call real DashScope services and build a full local index from the 8-manual M3 corpus. It is not yet a retrieval-quality benchmark.

Current smoke observations:

- `X1 Carbon battery removal` correctly requires clarification because generation is missing.
- `X1 Carbon Gen 9 battery removal` and `21CB battery removal` return results from the expected manuals after the hard-filter fix.
- Battery-removal queries currently rank safety-warning records above FRU procedure records in some cases.
- Exact error-code and safety queries return structured evidence, but their Hit@K/MRR are still unmeasured.

M6 should convert these smoke findings into a small golden evaluation set with measurable Hit@K, MRR, citation accuracy, model/generation accuracy, record-type accuracy, and safety-warning recall.
