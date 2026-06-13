# M8.4b Human Gold Evaluation Report

Date: 2026-06-13

## Scope

M8.4b finalizes the first human-reviewed gold fixture from the M8.4a review pack. It does not change agent behavior and does not run live providers in this session because `DASHSCOPE_API_KEY` was not present in the shell.

Committed artifact:

- `tests/fixtures/thinkpad_m8_4_human_gold_set.json`

Local ignored artifacts:

- `data/eval/m8_4_human_gold_finalize_audit.json`
- `data/eval/m8_4_human_det_strict.json`
- `data/eval/m8_4_120_det_strict.json`

## Human Review Outcome

The human-reviewed Markdown file was treated as authoritative because the generated JSON review pack still had all cases marked `pending`.

| Review Status | Count |
|---|---:|
| `verified` | 13 |
| `corrected` | 2 |
| `rejected` | 3 |
| Total | 18 |

Accepted committed cases:

| Category | Count |
|---|---:|
| `human_fru_procedure` | 6 |
| `human_fru_dependency_chain` | 3 |
| `human_table` | 4 |
| `human_negative` | 2 |
| Total | 15 |

Rejected cases:

- `m8_4a_thinkpad_t14_gen2_p14s_gen2_hmm_warning_battery`
- `m8_4a_thinkpad_t14_gen3_p14s_gen3_hmm_warning_battery`
- `m8_4a_thinkpad_t480_hmm_warning_battery`

These were page-3 table-of-contents false positives from the current safety extractor. They were not forced into the gold set.

## Evaluator Change

M8.4b narrows one strict citation metric:

- `citation_accuracy` remains result-level: it asks whether any returned citation hits an expected manual/page.
- `required_evidence_coverage` now uses per-step page coverage for `fru_procedure` repair steps when expected pages are present.

This prevents a multi-step procedure from passing strict page coverage merely because one unrelated result-level citation hit an expected page. Non-procedure supporting steps such as warnings, figures, and dependency-chain evidence may cite different pages and are not penalized by this FRU procedure page metric.

## Human Gold Deterministic Strict Result

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_4_human_gold_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --strict-citation --output data\eval\m8_4_human_det_strict.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 15 |
| Failed cases | 3 |
| `passed_case_rate` | 0.8000 |
| `final_plan_status_accuracy` | 0.8000 |
| `trajectory_tool_sequence_accuracy` | 0.8000 |
| `required_tool_coverage` | 0.9000 |
| `strict_citation_accuracy` | 0.7692 |
| `required_evidence_coverage` | 0.8462 |

Category pass rates:

| Category | Pass Rate |
|---|---:|
| `human_fru_procedure` | 1.0000 |
| `human_table` | 1.0000 |
| `human_negative` | 1.0000 |
| `human_fru_dependency_chain` | 0.0000 |

Failed cases:

| Case | Actual Status | Root Cause |
|---|---|---|
| `m8_4_thinkpad_p1_gen4_x1_extreme_gen4_hmm_chain_1030` | `not_found` | Agent intent routing does not treat "prerequisite chain" as a graph/dependency request. |
| `m8_4_thinkpad_e14_gen2_e15_gen2_hmm_chain_1020` | `not_found` | Same routing issue. |
| `m8_4_thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm_chain_1020` | `not_found` | Same routing issue. |

Interpretation: the first human gold set invalidates a direct M9 jump. FRU procedure, table, and negative behavior are clean on the reviewed sample, but dependency-chain natural-language routing must be fixed and retested.

## 120-Case Regression Result

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_2_reality_golden_set.json --manifest data\manifests\manuals_manifest.yaml --extracted-dir data\extracted\m3 --collection thinkpad_m4 --mode deterministic --strict-citation --output data\eval\m8_4_120_det_strict.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 120 |
| Failed cases | 0 |
| `passed_case_rate` | 1.0000 |
| `final_plan_status_accuracy` | 1.0000 |
| `strict_citation_accuracy` | 1.0000 |
| `required_evidence_coverage` | 1.0000 |

Interpretation: the old 120-case fixture remains a useful contract regression suite, but it did not catch the exact human phrasing "prerequisite chain". The human gold set is therefore now the higher-priority M9 gate.

## Safety Warning False Positive Root Cause

The rejected warning candidates come from the broad safety marker regex in `src/thinkpad/safety.py`, which currently treats any page containing words such as `battery` as safety-related. Page 3 in the rejected manuals is a table-of-contents page that mentions battery topics but does not contain the actual battery safety warning.

This should be fixed in a separate remediation step instead of being hidden by gold-set curation. The extractor should distinguish real warning blocks from TOC/index mentions.

## Decision

M8.4b is complete as a human-gold finalization and evaluator-integrity step, but the project should not proceed directly to full M9 packaging.

Recommended next milestone: M8.4c targeted remediation.

M8.4c should:

- Route dependency-chain phrasing such as "prerequisite chain" to `get_fru_dependency_chain`.
- Tighten safety warning extraction to avoid TOC/page-3 false positives.
- Generate a small replacement set of human warning candidates after the extractor fix.
- Re-run the M8.4 human gold deterministic strict evaluation and, when `DASHSCOPE_API_KEY` is available, a live retrieval check.
