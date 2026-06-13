# M8.2 Evaluation Reality Check

> Date: 2026-06-13
> Scope: anti-inflation benchmark, strict/raw metrics, harder 120-case fixture, live DashScope strict runs, and 24-record M3 extraction spot-check.
> Local raw reports: ignored under `data/eval/`.

## Summary

M8.2 confirms that the M8.1 `1.0000` results were valid contract-regression results, but not evidence of universal open-world repair-answer accuracy.

The original M8/M8.1 fixture checks whether the agent follows the expected contract: resolve model, call required tools, preserve at least minimum citations, avoid unsupported claims, and return expected status. M8.2 adds stricter scoring that separates:

- contract regression success.
- raw live LLM/provider quality.
- user-visible recovered success after M8.1 fallback.
- strict per-step citation behavior.
- harder alias, generation-interference, symptom, and plausible-unsupported cases.

## Why M8.1 Produced Many 1.0 Results

- The 96-case M8 fixture is a contract regression suite, not an open-world technician QA benchmark.
- Deterministic agent planning mainly uses structured evidence tools; live retrieval is often additional evidence, not the decision source.
- Only 36 of the 96 M8.1 live LLM cases scored `llm_citation_preservation`.
- M8.1 evidence-only fallback can recover malformed LLM output, missing citations, or provider failures. That improves user-visible behavior but must not be reported as raw LLM success.
- Previous citation accuracy accepted any expected manual/page hit. M8.2 adds stricter per-step citation scoring.
- The non-gold stress benchmark was already below 1.0 and exposed FRU procedure alias/applicability gaps.

## M8.2 Results

| Run | Cases | Failed | Pass Rate | Strict Citation Accuracy | Raw LLM Success | Provider Clean | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| deterministic strict | 120 | 74 | 0.3833 | 0.2708 | n/a | 1.0000 | Strict per-step citation makes the old contract-level 1.0 disappear. |
| live retrieval strict | 120 | 73 | 0.3917 | 0.3021 | n/a | 1.0000 | Retrieval helps some diagram/alias cases, but does not fix strict citation gaps. |
| raw live LLM strict | 120 | 82 | 0.3167 | 0.3021 | 0.0417 | 1.0000 | Strict mode disables evidence-only fallback and shows raw generation quality is weak. |
| stress live retrieval strict | 194 | 178 | 0.0825 | 0.1031 | n/a | 1.0000 | Stress cases are pressure tests, not gold truth; strict citation is intentionally harsh. |

The raw live LLM strict run was executed in six 20-case chunks after a single full run timed out. The combined ignored local report is `data/eval/m8_2_report_raw_live_llm_strict.json`.

## Main Findings

- M8.1 `1.0000` remains useful as a regression gate for deterministic tool orchestration.
- It should not be used as a resume/demo claim for open-ended repair-plan correctness.
- M8.2 strict citation shows that current expectations are not per-step enough for generated repair plans.
- Raw live LLM strict result is intentionally much lower than recovered M8.1 result: `raw_llm_success_rate=0.0417`, `llm_citation_preservation=0.0833`.
- Live retrieval provider path was stable in M8.2 strict runs: `provider_error_rate=0.0000`; one live retrieval strict run still recorded `retrieval_fallback_rate=0.0083`.
- Hard-case failures cluster around bottom/lower cover aliases, RAM/SIM-tray aliases, generation interference phrases, symptom-only repair requests, and plausible unsupported models returning clarification instead of not-found.

## Manual Spot-Check Records

This is a field-level spot-check over local ignored HMM PDFs and M3 JSONL artifacts. It validates page existence and record/citation signal alignment; it is not a full human audit of every extracted row.

| Manual | Type | Record ID | Page | Check | Result |
|---|---|---|---:|---|---|
| `thinkpad_t14_gen2_p14s_gen2_hmm` | procedure | `thinkpad_t14_gen2_p14s_gen2_hmm_fru_1010` | 72 | page range and heading signal | pass |
| `thinkpad_t14_gen2_p14s_gen2_hmm` | table | `thinkpad_t14_gen2_p14s_gen2_hmm_p040_t00_r001` | 40 | `table_type=error_code` | pass |
| `thinkpad_t14_gen2_p14s_gen2_hmm` | warning | `thinkpad_t14_gen2_p14s_gen2_hmm_p010_danger_0009` | 10 | `DANGER` | pass |
| `thinkpad_t14_gen3_p14s_gen3_hmm` | procedure | `thinkpad_t14_gen3_p14s_gen3_hmm_fru_1010` | 67 | page range and heading signal | pass |
| `thinkpad_t14_gen3_p14s_gen3_hmm` | table | `thinkpad_t14_gen3_p14s_gen3_hmm_p038_t00_r001` | 38 | `table_type=error_code` | pass |
| `thinkpad_t14_gen3_p14s_gen3_hmm` | figure | `thinkpad_t14_gen3_p14s_gen3_hmm_p001_img01` | 1 | image ID and page | pass |
| `thinkpad_t480_hmm` | procedure | `thinkpad_t480_hmm_fru_1010` | 70 | page range and heading signal | pass |
| `thinkpad_t480_hmm` | table | `thinkpad_t480_hmm_p042_t00_r001` | 42 | `table_type=error_code` | pass |
| `thinkpad_t480_hmm` | warning | `thinkpad_t480_hmm_p010_danger_0010` | 10 | `DANGER` | pass |
| `thinkpad_t490_hmm` | procedure | `thinkpad_t490_hmm_fru_1010` | 70 | page range and heading signal | pass |
| `thinkpad_t490_hmm` | table | `thinkpad_t490_hmm_p043_t00_r001` | 43 | `table_type=error_code` | pass |
| `thinkpad_t490_hmm` | figure | `thinkpad_t490_hmm_p001_img01` | 1 | image ID and page | pass |
| `thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm` | procedure | `thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm_fru_1020` | 74 | page range and heading signal | pass |
| `thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm` | table | `thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm_p042_t00_r001` | 42 | `table_type=error_code` | pass |
| `thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm` | warning | `thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm_p010_danger_0010` | 10 | `DANGER` | pass |
| `thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm` | procedure | `thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm_fru_1020` | 72 | page range and heading signal | pass |
| `thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm` | table | `thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm_p040_t00_r001` | 40 | `table_type=error_code` | pass |
| `thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm` | figure | `thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm_p001_img01` | 1 | image ID and page | pass |
| `thinkpad_e14_gen2_e15_gen2_hmm` | procedure | `thinkpad_e14_gen2_e15_gen2_hmm_fru_1020` | 67 | page range and heading signal | pass |
| `thinkpad_e14_gen2_e15_gen2_hmm` | table | `thinkpad_e14_gen2_e15_gen2_hmm_p039_t00_r001` | 39 | `table_type=error_code` | pass |
| `thinkpad_e14_gen2_e15_gen2_hmm` | warning | `thinkpad_e14_gen2_e15_gen2_hmm_p010_danger_0010` | 10 | `DANGER` | pass |
| `thinkpad_p1_gen4_x1_extreme_gen4_hmm` | procedure | `thinkpad_p1_gen4_x1_extreme_gen4_hmm_fru_1010` | 67 | page range and heading signal | pass |
| `thinkpad_p1_gen4_x1_extreme_gen4_hmm` | table | `thinkpad_p1_gen4_x1_extreme_gen4_hmm_p042_t00_r001` | 42 | `table_type=error_code` | pass |
| `thinkpad_p1_gen4_x1_extreme_gen4_hmm` | figure | `thinkpad_p1_gen4_x1_extreme_gen4_hmm_p001_img01` | 1 | image ID and page | pass |

## Decision

M8.2 is an evaluation integrity gate, not a product-quality remediation. It succeeds because it makes the measurement honest:

- keep M8.1 recovered path for user-visible robustness.
- report raw strict LLM quality separately.
- do not present strict M8.2 metrics as a demo failure; present them as anti-inflation evidence.
- before exposing `plan_repair` as MCP, improve per-step citation expectations, component alias normalization, and unsupported-generation classification.
