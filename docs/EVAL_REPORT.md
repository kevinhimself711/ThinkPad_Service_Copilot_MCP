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

## M6 ThinkPad Evaluation Baseline

- Date: 2026-06-12
- Milestone: M6 Evaluation Baseline + Lightweight Dashboard
- Golden set: `tests/fixtures/thinkpad_m6_golden_set.json`
- Cases: 30
- Scope: M5 evidence tools, structured lookups, model resolution, citation checks, and live retrieval smoke
- Out of scope: generated repair answers, Ragas faithfulness, Graph RAG traversal, agent trajectories

### Structured Baseline

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

Structured run result:

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
| `identifier_hit_at_k` | 0.9286 |

### Live Retrieval Baseline

Live run used `DASHSCOPE_API_KEY` only from the local shell. The key was not written to repository files.

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

Live run result:

| Metric | Value |
|---|---:|
| Query count | 30 |
| Evaluated cases | 30 |
| Skipped cases | 0 |
| Failed cases | 1 |
| Passed case rate | 0.9667 |
| `tool_status_accuracy` | 0.9667 |
| `clarification_accuracy` | 1.0000 |
| `manual_hit_at_k` | 0.9500 |
| `manual_mrr` | 0.9100 |
| `record_type_hit_at_k` | 0.9286 |
| `record_type_mrr` | 0.9286 |
| `citation_coverage` | 0.9375 |
| `citation_accuracy` | 0.9375 |
| `identifier_hit_at_k` | 0.9333 |
| `empty_unexpected_result_rate` | 0.0000 |
| `latency_ms_p50` | 0.0 |
| `latency_ms_p95` | 1445.8 |

Category finding:

- `live_retrieval` passed all 4 live cases with `manual_hit_at_k=1.0`, `manual_mrr=1.0`, `record_type_hit_at_k=1.0`, and `citation_accuracy=1.0`.
- `screw_spec` had the only failed case.

Failed case:

| Case | Expected | Actual | Interpretation |
|---|---|---|---|
| `m6_screw_t480_exact_size` | `ok` screw table hit for `M2 x 3` | `not_found` | The query used ASCII `x`, while extracted PDF text uses the multiplication sign `×`; exact lookup needs screw-spec normalization. |

### Interpretation

M6 proves that ThinkPad evidence tools are measurable with a domain-specific golden set and that live retrieval can be evaluated without answer generation. It also exposes a concrete normalization gap for exact screw-size lookup. The next retrieval-quality work should fix screw-spec normalization and then re-run the same M6 golden set to show before/after movement.

## M6.1 Screw-Spec Normalization Remediation

- Date: 2026-06-12
- Scope: targeted M6.1 remediation before M7 Graph RAG
- Golden set: unchanged `tests/fixtures/thinkpad_m6_golden_set.json`
- Code path fixed: structured exact lookup in `ThinkPadToolService.get_screw_spec()`
- Out of scope: MCP schema changes, new golden cases, answer generation, FRU graph traversal

### Fix Summary

M6 exposed one real failure: `m6_screw_t480_exact_size` queried `M2 x 3`, while extracted PDF text represented the same screw size with the multiplication sign. M6.1 keeps the golden case unchanged and normalizes lookup text so equivalent screw-size expressions match:

- `M2 x 3`
- `M2 X 3`
- `M2*3`
- `M2x3`
- `M2 x 3 mm`

Error-code exact matching remains on the separate `_contains_exact_code()` path.

### Before And After

| Run | Evaluated | Skipped | Failed | `tool_status_accuracy` | `manual_hit_at_k` | `manual_mrr` | `record_type_hit_at_k` | `citation_accuracy` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 structured baseline | 26 | 4 | 1 | 0.9615 | 0.9444 | 0.9000 | 0.9231 | 0.9231 |
| M6 live baseline | 30 | 0 | 1 | 0.9667 | 0.9500 | 0.9100 | 0.9286 | 0.9375 |
| M6.1 structured after fix | 26 | 4 | 0 | 1.0000 | 1.0000 | 0.9556 | 1.0000 | 1.0000 |
| M6.1 live after fix | 30 | 0 | 0 | 1.0000 | 1.0000 | 0.9600 | 1.0000 | 1.0000 |

M6.1 live retrieval also reported `identifier_hit_at_k=1.0000`, `citation_coverage=1.0000`, `empty_unexpected_result_rate=0.0000`, and `latency_ms_p95=6268.05`. The higher p95 latency than M6 is recorded as provider/runtime variation and should not be interpreted as a quality regression.

### Decision

M6.1 closes the only M6 golden-set failure without weakening the evaluation target. M7 can proceed to FRU dependency graph work, but should keep using the M6/M6.1 golden set as a regression suite.

## M7 FRU Dependency Graph Baseline

- Date: 2026-06-12
- Milestone: M7 FRU Dependency Graph + `get_fru_dependency_chain`
- Golden set: `tests/fixtures/thinkpad_m7_golden_set.json`
- Cases: 36
- Added graph cases: 6
- Scope: structured FRU dependency graph traversal and MCP evidence output
- Out of scope: natural-language repair plans, Agent workflow, live retrieval tuning, new HMM download, graph database

### Structured Evaluation

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

Structured run result:

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
| `record_type_mrr` | 1.0000 |
| `citation_coverage` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `identifier_hit_at_k` | 1.0000 |

Graph category result:

| Metric | Value |
|---|---:|
| Graph `ok` cases | 4 |
| Graph ambiguity cases | 1 |
| Graph negative cases | 1 |
| Failed graph cases | 0 |
| `manual_hit_at_k` | 1.0000 |
| `record_type_hit_at_k` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `identifier_hit_at_k` | 1.0000 |

### Interpretation

M7 proves that M3 dependency edges can be traversed as structured graph evidence and exposed through MCP without LLM calls or live retrieval. The graph tool returns cited prerequisite chains, missing-node metadata, and cycle flags; it does not produce final technician instructions.

M8 can now use `get_fru_dependency_chain` as one evidence tool inside a repair-planning agent, but generated plan faithfulness still needs separate evaluation.

## M7.1 M0-M7 Audit And Live Regression

- Date: 2026-06-12
- Scope: pre-M8 audit gate for M0-M7 completion evidence
- Report: `docs/M0_M7_PROGRESS_AUDIT.md`
- Local audit JSON: ignored `data/eval/m0_m7_audit.json`
- Live provider: DashScope via local `DASHSCOPE_API_KEY` environment variable only
- Out of scope: M8 Agent Client, new HMM downloads, full index rebuild, answer generation

### Regression Results

| Check | Result |
|---|---|
| ThinkPad tests | Passed, 78 tests, after rerunning with ignored pytest basetemp because the default Windows temp root returned a permission error |
| Smoke imports | Passed, 22 tests |
| Dashboard smoke | Passed, 8 tests |
| Ruff scoped check | Passed |
| M7 structured eval | Passed, 32 evaluated, 4 live retrieval cases skipped, 0 failed |
| M7 live eval | Passed, 36 evaluated, 0 skipped, 0 failed |

### M7 Live Evaluation Metrics

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
| `citation_coverage` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `identifier_hit_at_k` | 1.0000 |
| `empty_unexpected_result_rate` | 0.0000 |
| `latency_ms_p95` | 5339.75 |

### Audit Decision

M0-M7 meet their intended milestone goals, but the audit keeps three boundaries explicit:

- M1/M3/M7 produce structured candidates and graph evidence, not fully human-audited HMM truth.
- M4/M6/M7 metrics cover the current curated golden sets, not a final 80-100 case benchmark.
- M5/M7 return evidence JSON; generated repair-plan quality belongs to M8 and must be evaluated separately.

Decision: M8 can proceed after committing the M7.1 audit artifacts.
