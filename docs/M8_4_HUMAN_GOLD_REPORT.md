# M8.4 Human Gold And Live Baseline Report

Date: 2026-06-13

## Scope

M8.4 closes the evaluation-integrity gap before M9. It has three parts:

- M8.4a generated a local human-review pack.
- M8.4b converted reviewed cases into a committed human gold fixture and tightened FRU procedure page scoring.
- M8.4c fixed the two blockers exposed by M8.4b and ran the originally required DashScope live baselines.

Committed artifacts:

- `tests/fixtures/thinkpad_m8_4_human_gold_set.json`
- `tests/fixtures/thinkpad_m8_2_reality_golden_set.json`

Ignored local reports:

- `data/eval/m8_4c_human_det_strict.json`
- `data/eval/m8_4c_human_live_retrieval_strict.json`
- `data/eval/m8_4c_human_raw_live_llm_strict.json`
- `data/eval/m8_4c_120_det_strict.json`
- `data/eval/m8_4c_120_live_retrieval_strict.json`
- `data/eval/m8_4c_120_raw_live_llm_strict.json`

No PDFs, extracted full text, provider output dumps, vector stores, or API keys are committed.

## Human Gold Outcome

M8.4b started from 18 manually reviewed candidates:

| Review Status | Count |
|---|---:|
| `verified` | 13 |
| `corrected` | 2 |
| `rejected` | 3 |
| Total | 18 |

The 3 rejected cases were page-3 table-of-contents battery-warning false positives. M8.4c fixed TOC/index filtering in `src/thinkpad/safety.py` and added 3 replacement warning cases verified against real warning pages.

Final committed human gold fixture:

| Category | Count |
|---|---:|
| `human_fru_procedure` | 6 |
| `human_fru_dependency_chain` | 3 |
| `human_table` | 4 |
| `human_warning` | 3 |
| `human_negative` | 2 |
| Total | 18 |

## M8.4c Fixes

### Dependency-Chain Routing

M8.4b found 3 human-gold failures where queries such as "prerequisite chain" did not route to graph evidence. M8.4c updates the agent intent detector so these phrases call `get_fru_dependency_chain` directly:

- `prerequisite chain`
- `dependency chain`
- `required FRUs`
- `before removing`
- related "what must be removed before" phrasing

The 120-case regression fixture was updated for `fru_dependency_chain` cases to expect the direct graph evidence trajectory:

```text
resolve_thinkpad_model -> get_fru_dependency_chain
```

That is an expectation correction, not a lowered evidence standard. Chain-only queries should not be forced to call procedure, diagram, or safety tools.

### Safety Warning False Positives

M8.4c adds TOC/index-page filtering before safety marker extraction. A page headed `Contents`, `Table of Contents`, or `Index` with dotted leader/chapter listing patterns is skipped even if it contains words such as `battery`.

True warning blocks with `DANGER`, `CAUTION`, `Attention`, ESD, battery, or system-board safety signals still produce cited `WarningRecord` entries.

## Strict Baseline Results

| Run | Cases | Failed | Pass Rate | Provider Error | Raw LLM Success | p95 Latency |
|---|---:|---:|---:|---:|---:|---:|
| Human deterministic strict | 18 | 0 | 1.0000 | 0.0000 | n/a | 31 ms |
| Human live retrieval strict | 18 | 0 | 1.0000 | 0.0000 | n/a | 1422 ms |
| Human raw live LLM strict | 18 | 2 | 0.8889 | 0.1111 | 0.7778 | 61844 ms |
| 120-case deterministic strict | 120 | 0 | 1.0000 | 0.0000 | n/a | 32 ms |
| 120-case live retrieval strict | 120 | 0 | 1.0000 | 0.0000 | n/a | 1437 ms |
| 120-case raw live LLM strict | 120 | 2 | 0.9833 | 0.0167 | 0.9583 | 43906 ms |

All deterministic and live retrieval runs have:

- `strict_citation_accuracy=1.0000`
- `required_tool_coverage=1.0000`
- `trajectory_tool_sequence_accuracy=1.0000`
- `retrieval_fallback_rate=0.0000`

Raw live LLM strict failures are preserved as real failures:

| Run | Case | Root Cause |
|---|---|---|
| Human raw live LLM strict | `m8_4_thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm_fru_1020` | `provider_timeout` |
| Human raw live LLM strict | `m8_4_thinkpad_p1_gen4_x1_extreme_gen4_hmm_chain_1030` | `provider_timeout` |
| 120-case raw live LLM strict | `m8_fru_thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm_1030` | `provider_timeout` |
| 120-case raw live LLM strict | `m8_2_cross_t14g3_not_g2` | `provider_timeout` |

## Interpretation

M8.4c completes the original M8.4 scope:

- Human-reviewed pages are now represented in a committed fixture.
- The dependency-chain routing defect found by human gold is fixed.
- TOC battery-warning false positives are filtered.
- Deterministic, live retrieval, and raw live LLM strict baselines were run with DashScope.

The results should still be described carefully:

- The deterministic and live retrieval `1.0000` results are benchmark-contract results over defined fixtures, not universal open-world repair accuracy.
- Raw live LLM strict is materially better than M8.2 and usable for controlled demos, but provider timeouts remain visible.
- The default demo path should use deterministic validation and evidence fallback. Raw LLM-only planning should remain a reported provider-quality mode.

## Decision

M8.4c removes the M8.4b blockers and closes the live-baseline omission. The project can proceed to M9 packaging and interview readiness, with one boundary: do not expose raw LLM-only repair planning as the default behavior. Any later `plan_repair` MCP exposure should keep deterministic validation and evidence-grounded fallback.
