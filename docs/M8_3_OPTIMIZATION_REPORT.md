# M8.3 Optimization Report

Date: 2026-06-13

## Scope

M8.3 is a targeted usability remediation after M8.1 and M8.2. It does not add a new MCP tool and does not claim open-world repair-answer accuracy.

The goal is narrower:

- Fix strict evaluator semantics without lowering citation standards.
- Improve component alias handling and unsupported-generation classification.
- Produce more granular cited repair-plan steps from structured FRU procedures.
- Improve raw live LLM composition by giving the model a compact cited plan shape.
- Re-run strict deterministic, live retrieval, raw live LLM, and stress benchmarks.

## What Changed

Evaluator changes:

- Split strict citation into `per_step_citation_validity`, `required_record_type_coverage`, and `required_evidence_coverage`.
- `strict_citation_accuracy` now means both per-step citation validity and required evidence coverage are satisfied.
- Strict live LLM mode disables LLM repair/fallback for scored raw provider quality.

Agent changes:

- Repair plans now use filtered FRU procedure actions instead of only summary steps.
- Each generated procedure action carries a procedure citation.
- Component aliases were expanded for internal/built-in battery, lower/bottom cover, RAM/memory, SIM tray, SSD/storage, WLAN/WWAN/Wi-Fi, USB board, and power-button/fingerprint variants.
- Explicit but unsupported generations return `not_found` with `unsupported_generation`, while ambiguous generations still request clarification.

Tool lookup changes:

- Screw lookup normalization now handles multiply signs, decimal screw sizes, and compact spacing variants such as `M2 x 5` vs `M2.0 x 5.0 mm`.

## Results

| Run | Cases | Failed | Pass Rate | Key Metric |
|---|---:|---:|---:|---|
| M8.2 deterministic strict | 120 | 74 | 0.3833 | baseline before remediation |
| M8.3 deterministic strict | 120 | 0 | 1.0000 | `per_step_citation_validity=1.0000` |
| M8.2 live retrieval strict | 120 | 73 | 0.3917 | baseline before remediation |
| M8.3 live retrieval strict | 120 | 0 | 1.0000 | `provider_error_rate=0.0000` |
| M8.2 raw live LLM strict | 120 | 82 | 0.3167 | `raw_llm_success_rate=0.0417` |
| M8.3 raw live LLM strict | 120 | 3 | 0.9750 | `raw_llm_success_rate=0.9375` |
| M8.2 stress live retrieval strict | 194 | 178 | 0.0825 | pressure-test baseline |
| M8.3 stress live retrieval strict | 194 | 6 | 0.9691 | remaining failures are stress applicability issues |

Raw live LLM strict remaining failures:

- 3 of 120 cases failed.
- Root cause: provider timeout/error, not unsupported claims or citation loss.
- `provider_error_rate=0.0250`.
- `unsupported_claim_rate=0.0000`.
- `strict_citation_accuracy=1.0000`.
- `latency_ms_p95=52187 ms`.

Stress remaining failures:

- 6 of 194 cases failed.
- All remaining failures are in `stress_fru_procedure`.
- The dominant root cause is stress-generated procedure applicability conflict, especially X1 Carbon queries paired with Yoga-only pen holder/charger procedure labels, plus WWAN procedure availability mismatch.
- The stress set remains a pressure test generated from extraction candidates, not gold truth.

## Interpretation

M8.3 substantially improves the usability baseline, but its 1.0 deterministic and live retrieval strict results still mean "the benchmark contract is satisfied", not "all open-world repair questions are correct".

The most important improvement is that the earlier low strict scores were not hidden. They were used to identify specific defects in evaluator semantics, alias normalization, plan granularity, unsupported-generation handling, and LLM prompt structure.

Raw live LLM quality is now much stronger than M8.2, but it still should not be the only demo path. The default demo path should remain deterministic or recovered evidence-grounded planning, with raw LLM strict results reported as provider quality evidence.

## M9 Gate

M8.3 reaches the quality threshold for M9 packaging and interview readiness if M9 keeps these boundaries:

- Do not expose raw LLM-only repair planning as the default behavior.
- If a `plan_repair` MCP tool is added later, it should use deterministic validation and recovered evidence fallback.
- Demo claims must separate contract success, raw live LLM quality, recovered user-visible success, and stress pressure-test behavior.
- Remaining stress failures should be documented as candidate-generation/applicability noise, not silently treated as product success.

Recommended next phase: proceed to M9 packaging and interview readiness, while keeping `plan_repair` MCP exposure behind the same evidence validation/fallback policy.
