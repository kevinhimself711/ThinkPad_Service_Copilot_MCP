# M8.1 Agent Reliability Remediation Report

> Date: 2026-06-13
> Scope: LLM composition hardening, provider-fallback scoring, stress candidate cleanup, and M8 before/after evaluation.
> Local raw reports: ignored under `data/eval/`.

## Summary

M8.1 remediates the M8 agent reliability gaps without adding a new MCP tool. The main change is to treat live LLM output as a candidate that must pass deterministic validation. If LLM output is malformed, misses citations, or the provider fails, the agent can use a local evidence-only normalizer to produce a cited JSON plan from the already retrieved `EvidenceBundle`.

This keeps the source of truth in the evidence tools. The fallback is not allowed to invent FRU IDs, screw specs, torque values, error codes, warnings, or citations.

## Before And After

| Run | M8 Failed | M8.1 Failed | M8 Metric | M8.1 Metric | Interpretation |
|---|---:|---:|---:|---:|---|
| Deterministic 96-case | 0 | 0 | pass rate 1.0000 | pass rate 1.0000 | No regression in deterministic orchestration. |
| Live retrieval 96-case | 0 | 0 | fallback 0.0417 | fallback 0.1354 | Retrieval still passes; rerank fallback rate increased in this live run. |
| Live LLM 96-case | 5 | 0 | pass rate 0.9479 | pass rate 1.0000 | LLM/provider/citation failures are recovered by validation and evidence-only fallback. |
| Stress deterministic 194-case | 17 | 10 | pass rate 0.9124 | pass rate 0.9485 | Diagnostic pseudo-FRU filtering and aliases reduced candidate noise. |
| Stress live retrieval 194-case | 17 | 10 | pass rate 0.9124 | pass rate 0.9485 | Live retrieval does not hide remaining structured-procedure gaps. |

## M8.1 Live LLM Result

Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py `
  --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json `
  --manifest data\manifests\manuals_manifest.yaml `
  --extracted-dir data\extracted\m3 `
  --collection thinkpad_m4 `
  --live-llm `
  --llm-repair-attempts 1 `
  --output data\eval\m8_1_agent_report_live_llm.json
```

Result:

| Metric | Value |
|---|---:|
| Cases | 96 |
| Failed cases | 0 |
| `passed_case_rate` | 1.0000 |
| `final_plan_status_accuracy` | 1.0000 |
| `llm_citation_preservation` | 1.0000 |
| `unsupported_claim_rate` | 0.0000 |
| `provider_error_rate` | 0.0104 |
| `latency_ms_p50` | 1375 |
| `latency_ms_p95` | 90015 |

Provider errors are still counted as provider errors. They no longer automatically fail a case when the response status, citations, identifiers, and required evidence remain valid after fallback.

## Stress Result

M8.1 regenerated local stress candidates from M3 extraction artifacts and filtered obvious diagnostic pseudo-FRUs:

- `2201 Machine UUID is invalid`
- `2204 System configuration data is invalid`
- `2205 Sensor configuration failure`

Stress live retrieval result:

| Metric | Value |
|---|---:|
| Cases | 194 |
| Failed cases | 10 |
| `passed_case_rate` | 0.9485 |
| `citation_accuracy` | 0.9794 |
| `evidence_identifier_coverage` | 0.9731 |
| `retrieval_fallback_rate` | 0.0258 |
| `unsupported_claim_rate` | 0.0000 |

Remaining stress failures are concentrated in FRU procedure candidates whose raw extracted names do not map cleanly to current exact component lookup, for example:

- USB board / USB board cable / USB board bracket.
- Wireless WAN card on X1 Carbon Gen 9 / Gen 10 stress candidates.
- Power button / fingerprint reader module and cable.

These failures are not gold-set failures. They are useful hardening targets for component aliasing and extraction-candidate review.

## Implementation Decision

M8.1 meets the remediation target:

- deterministic 96-case remains clean.
- live retrieval 96-case remains clean.
- live LLM 96-case improves from 5 failed to 0 failed.
- `llm_citation_preservation` improves from 0.8611 to 1.0000.
- `unsupported_claim_rate` improves from 0.0521 to 0.0000.
- stress failures decrease from 17 to 10 and are grouped by root cause.

M9 can proceed to packaging and interview readiness, but demo scripts should still expose provider fallback metrics instead of claiming provider calls are always clean.
