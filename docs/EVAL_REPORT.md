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

## M8 Repair-Planning Agent Baseline

- Date: 2026-06-12
- Milestone: M8 Repair-Planning Agent + Scaled Performance Evaluation
- Canonical performance report: `docs/M8_AGENT_PERFORMANCE_BASELINE.md`
- Golden set: `tests/fixtures/thinkpad_m8_agent_golden_set.json`
- Golden cases: 96
- Stress candidates: 194 local generated cases under ignored `data/eval/`
- Live provider: DashScope through local `DASHSCOPE_API_KEY`; no key or raw provider output committed
- Out of scope: new MCP tool, production answer endpoint, Ragas faithfulness, new HMM downloads, committed provider traces

### Why M8 Has Separate Metrics

M7 evidence-tool metrics reached 1.0 on the current 36-case gate, but those metrics do not measure generated repair-plan quality. M8 therefore evaluates three separate layers:

| Layer | What It Measures | M8 Evidence |
|---|---|---|
| Evidence tools | Whether structured tools return cited evidence | M7 structured/live regression stays clean |
| Agent trajectory | Whether the agent selects the expected tools and preserves evidence | M8 deterministic and live retrieval 96-case runs |
| Generated plan faithfulness | Whether live LLM composition preserves citations and avoids unsupported claims | M8 live LLM 96-case run |

### 96-Case Golden Set

| Category | Cases |
|---|---:|
| Model ambiguity / clarification | 12 |
| Exact machine-type resolution | 8 |
| Error-code or diagnostic evidence | 12 |
| Screw / torque evidence | 12 |
| FRU procedure plans | 16 |
| Dependency-chain plans | 12 |
| Diagram citation requirements | 8 |
| Safety-warning requirements | 8 |
| Unsupported / negative cases | 8 |
| Total | 96 |

### Baseline Runs

| Run | Cases | Failed | Pass Rate | Provider Error Rate | Retrieval Fallback Rate | Unsupported Claim Rate | p50 Latency | p95 Latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Deterministic 96-case | 96 | 0 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 15 ms | 16 ms |
| Live retrieval 96-case | 96 | 0 | 1.0000 | 0.0000 | 0.0417 | 0.0000 | 1344 ms | 6032 ms |
| Live LLM 96-case | 96 | 5 | 0.9479 | 0.0521 | 0.0833 | 0.0521 | 4359 ms | 59000 ms |
| Stress deterministic | 194 | 17 | 0.9124 | 0.0000 | 0.0000 | 0.0000 | 15 ms | 16 ms |
| Stress live retrieval | 194 | 17 | 0.9124 | 0.0000 | 0.0309 | 0.0000 | 1375 ms | 6047 ms |

### Deterministic Agent Result

The deterministic run passed all 96 committed golden cases.

| Metric | Value |
|---|---:|
| `final_plan_status_accuracy` | 1.0000 |
| `trajectory_tool_sequence_accuracy` | 1.0000 |
| `required_tool_coverage` | 1.0000 |
| `clarification_accuracy` | 1.0000 |
| `citation_coverage` | 1.0000 |
| `citation_accuracy` | 1.0000 |
| `evidence_identifier_coverage` | 1.0000 |
| `safety_warning_inclusion` | 1.0000 |

Interpretation: deterministic agent orchestration is clean for the committed M8 fixture. This proves tool sequencing and citation plumbing, not open-ended answer generation quality.

### Live Retrieval Result

The live retrieval run passed all 96 committed golden cases. It recorded provider fallback events instead of hiding them:

- `retrieval_fallback_rate=0.0417`
- observed fallback type: DashScope rerank connection resets falling back to deterministic fused/domain-ranked evidence

Interpretation: the agent can run through the live retrieval path at 96-case scale, and the fallback path is real. The run does not prove every possible technician query will retrieve the right evidence.

### Live LLM Result

The live LLM run completed all 96 cases, with LLM composition required for 36 cases. Five cases failed.

| Case | Category | Interpretation |
|---|---|---|
| `m8_fru_thinkpad_t480_hmm_1010` | FRU procedure | live LLM/provider composition failure |
| `m8_fru_thinkpad_t490_hmm_1020` | FRU procedure | live LLM/provider composition failure |
| `m8_fru_thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm_1030` | FRU procedure | live LLM/provider composition failure |
| `m8_fru_thinkpad_p1_gen4_x1_extreme_gen4_hmm_1010` | FRU procedure | live LLM/provider composition failure |
| `m8_chain_thinkpad_t480_hmm_1020` | Dependency-chain plan | live LLM/provider composition failure |

Key live LLM metrics:

| Metric | Value |
|---|---:|
| `llm_citation_preservation` | 0.8611 |
| `provider_error_rate` | 0.0521 |
| `unsupported_claim_rate` | 0.0521 |
| `citation_accuracy` | 1.0000 |
| `required_tool_coverage` | 1.0000 |

Interpretation: the evidence layer remained available, but live answer composition is not yet clean. M8 should be presented as a measured first agent baseline with a clear remediation path, not as a perfect final repair-answer system.

### Stress Benchmark

The stress generator produced 194 local cases from M3 extraction records. These are not gold cases because they inherit extraction-candidate noise.

Stress findings:

- Deterministic and live retrieval stress both had 17 failed cases.
- Failures are mainly caused by diagnostic pseudo-FRU IDs and component alias gaps from raw extraction labels.
- Live retrieval improved citation/identifier coverage among successful stress cases but did not resolve candidate-generation noise.

Decision: keep the 96-case fixture as the canonical M8 gold baseline and use the stress set to drive M8/M9 hardening work.

### M8 Decision

M8 meets its implementation and scaled-evaluation goals with risk:

- `complete`: local repair-planning agent client, deterministic orchestration, CLIs, agent evaluator, 96-case fixture, docs, and tests.
- `complete_with_risk`: live LLM generated-plan path, because 5/96 cases failed and `llm_citation_preservation` is below 1.0.

Next remediation should focus on LLM composer retries, stricter structured output validation, and component alias cleanup before exposing a final `plan_repair` MCP tool.

## M8.1 Agent Reliability Remediation

- Date: 2026-06-13
- Milestone: M8.1 Agent Reliability Remediation
- Canonical report: `docs/M8_1_REMEDIATION_REPORT.md`
- Raw local reports: ignored under `data/eval/`
- Scope: LLM composition validation/fallback, provider-error scoring, stress pseudo-FRU cleanup, and before/after evaluation
- Out of scope: new MCP tool, new HMM download, committed provider traces, production packaging

### Before And After

| Run | M8 Failed | M8.1 Failed | M8.1 Key Metric |
|---|---:|---:|---|
| Deterministic 96-case | 0 | 0 | pass rate 1.0000 |
| Live retrieval 96-case | 0 | 0 | fallback rate 0.1354 |
| Live LLM 96-case | 5 | 0 | `llm_citation_preservation=1.0000`, `unsupported_claim_rate=0.0000` |
| Stress deterministic 194-case | 17 | 10 | pass rate 0.9485 |
| Stress live retrieval 194-case | 17 | 10 | pass rate 0.9485 |

### Interpretation

M8.1 separates generated-plan quality from provider cleanliness:

- Live LLM generated-plan validation is now clean for the 96-case golden set.
- Provider errors are still counted through `provider_error_rate`; a recovered provider issue does not fail the case if status, citations, identifiers, and required evidence are valid.
- The remaining 10 stress failures are non-gold extraction/alias issues in FRU procedure candidates, not live provider failures.

Decision: M8.1 closes the M8 live LLM demo blocker. M9 can proceed, while keeping stress FRU alias/applicability cleanup as a follow-up hardening item.

## M8.2 Evaluation Reality Check

- Date: 2026-06-13
- Milestone: M8.2 Evaluation Reality Check + Anti-Inflation Benchmark
- Canonical report: `docs/M8_2_EVAL_REALITY_CHECK.md`
- New fixture: `tests/fixtures/thinkpad_m8_2_reality_golden_set.json`
- Raw local reports: ignored under `data/eval/`
- Scope: strict/raw evaluator metrics, 120-case anti-inflation fixture, live DashScope strict runs, and 24-record extraction spot-check

### Why This Exists

M8.1 produced several `1.0000` metrics because it was primarily a contract regression gate. That result is useful, but it must not be described as universal open-world repair-answer accuracy.

M8.2 splits the interpretation:

- `contract regression`: status, required tools, citation plumbing, identifiers.
- `raw provider/LLM quality`: no repair fallback, strict citation preservation.
- `user-visible recovered success`: M8.1 fallback after deterministic validation.

### Strict Results

| Run | Cases | Failed | Pass Rate | Strict Citation Accuracy | Raw LLM Success | Provider Clean |
|---|---:|---:|---:|---:|---:|---:|
| deterministic strict | 120 | 74 | 0.3833 | 0.2708 | n/a | 1.0000 |
| live retrieval strict | 120 | 73 | 0.3917 | 0.3021 | n/a | 1.0000 |
| raw live LLM strict | 120 | 82 | 0.3167 | 0.3021 | 0.0417 | 1.0000 |
| stress live retrieval strict | 194 | 178 | 0.0825 | 0.1031 | n/a | 1.0000 |

Interpretation:

- M8.1 `1.0000` remains valid as a recovered contract-regression result.
- Raw live LLM strict quality is not ready to claim as independently reliable.
- Strict citation scoring is intentionally harsher than previous `citation_accuracy`; it exposes that expected pages/record types are not yet modeled per repair step.
- Live retrieval remained operational in M8.2, with `provider_error_rate=0.0000` in the strict runs.

### M8.2 Decision

M8.2 should be presented as evidence of evaluation integrity. It does not block M9 packaging, but M9 demo and README claims must distinguish recovered user-visible success from raw LLM/provider quality.

## M8.3 Systematic Diagnosis And Usability Optimization

- Date: 2026-06-13
- Milestone: M8.3 Systematic Diagnosis + Usability-Level Optimization
- Canonical report: `docs/M8_3_OPTIMIZATION_REPORT.md`
- Raw local reports: ignored under `data/eval/`
- Scope: strict evaluator semantics, component aliases, unsupported-generation classification, procedure-step planning, screw normalization, and strict/live benchmark reruns

### Before And After

| Run | Cases | Failed | Pass Rate | Notes |
|---|---:|---:|---:|---|
| M8.2 deterministic strict | 120 | 74 | 0.3833 | anti-inflation baseline |
| M8.3 deterministic strict | 120 | 0 | 1.0000 | strict contract now satisfied |
| M8.2 live retrieval strict | 120 | 73 | 0.3917 | anti-inflation baseline |
| M8.3 live retrieval strict | 120 | 0 | 1.0000 | provider error rate 0.0000 |
| M8.2 raw live LLM strict | 120 | 82 | 0.3167 | raw LLM baseline |
| M8.3 raw live LLM strict | 120 | 3 | 0.9750 | 3 provider timeout/error failures |
| M8.2 stress live retrieval strict | 194 | 178 | 0.0825 | pressure-test baseline |
| M8.3 stress live retrieval strict | 194 | 6 | 0.9691 | remaining failures are stress applicability conflicts |

M8.3 raw live LLM strict metrics:

- `raw_llm_success_rate=0.9375`
- `llm_citation_preservation=0.9375`
- `unsupported_claim_rate=0.0000`
- `strict_citation_accuracy=1.0000`
- `provider_error_rate=0.0250`
- `latency_ms_p95=52187 ms`

### Interpretation

M8.3 improves the system to a usable benchmark level, but the interpretation remains bounded:

- Deterministic and live retrieval `1.0000` are strict benchmark contract results, not open-world repair accuracy.
- Raw live LLM is now strong enough for controlled demos, but provider timeout/error remains visible and should not be hidden.
- The recovered live LLM path was not rerun in this M8.3 session because `DASHSCOPE_API_KEY` was not present in the shell at documentation time. The stricter raw live LLM full run was completed and is the stronger new generation-quality evidence.
- Stress failures are now concentrated in generated candidate applicability conflicts, not broad alias or citation plumbing failure.

### M8.3 Decision

M8.3 reaches the quality threshold to proceed to M9 packaging and interview readiness, with one boundary: do not expose raw LLM-only repair planning as the default path. Any later `plan_repair` MCP exposure should use deterministic validation and recovered evidence fallback.
