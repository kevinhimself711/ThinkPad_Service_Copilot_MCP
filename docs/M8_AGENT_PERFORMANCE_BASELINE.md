# M8 Agent Performance Baseline

> Date: 2026-06-12
> Scope: Repair-planning agent client, 96-case agent golden set, full live retrieval/LLM runs, and stress benchmark.
> Local raw reports: ignored under `data/eval/`.

## Summary

M8 adds a local ThinkPad repair-planning agent client over the existing M2-M7 evidence tools. The agent is intentionally narrow: it resolves the model, calls deterministic evidence tools, assembles cited evidence, and optionally asks DashScope LLM to rewrite that evidence into a cited repair plan. It does not expose a new MCP tool and does not let the LLM invent FRU IDs, screw specs, torque values, error codes, warnings, or citations.

The evaluation was deliberately scaled beyond the M7 gate:

- M7 used 36 evidence-tool cases, with only 4 live retrieval cases.
- M8 uses a 96-case agent golden set across 8 HMM manuals.
- M8 also runs a 194-case stress benchmark generated from M3 extraction artifacts.
- Live retrieval and live LLM baselines use DashScope through `DASHSCOPE_API_KEY` in the local shell only.

## Implemented Agent Surface

Primary API:

```python
plan_thinkpad_repair(
    query,
    service,
    use_llm=False,
    llm=None,
    collection="thinkpad_m4",
    top_k=5,
    use_retrieval=False,
    require_live_retrieval=False,
) -> RepairPlanResult
```

Primary CLIs:

```powershell
.\.venv\Scripts\python scripts\thinkpad_agent_plan.py "21CB battery removal plan"
.\.venv\Scripts\python scripts\thinkpad_agent_evaluate.py --golden-set tests\fixtures\thinkpad_m8_agent_golden_set.json --mode deterministic
.\.venv\Scripts\python scripts\thinkpad_generate_agent_eval_candidates.py --output data\eval\m8_agent_stress_candidates.json
```

## Golden Set Coverage

Committed fixture: `tests/fixtures/thinkpad_m8_agent_golden_set.json`.

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

The fixture stores only query metadata, expected statuses, required tool names, manual IDs, record types, citation requirements, and short identifiers. It does not commit Lenovo manual text, PDFs, diagrams, vector records, or provider outputs.

## Baseline Results

| Run | Cases | Failed | Pass Rate | Provider Error Rate | Retrieval Fallback Rate | Unsupported Claim Rate | p50 Latency | p95 Latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Deterministic 96-case | 96 | 0 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 15 ms | 16 ms |
| Live retrieval 96-case | 96 | 0 | 1.0000 | 0.0000 | 0.0417 | 0.0000 | 1344 ms | 6032 ms |
| Live LLM 96-case | 96 | 5 | 0.9479 | 0.0521 | 0.0833 | 0.0521 | 4359 ms | 59000 ms |
| Stress deterministic | 194 | 17 | 0.9124 | 0.0000 | 0.0000 | 0.0000 | 15 ms | 16 ms |
| Stress live retrieval | 194 | 17 | 0.9124 | 0.0000 | 0.0309 | 0.0000 | 1375 ms | 6047 ms |

### Deterministic 96-Case Baseline

The deterministic agent run passed all 96 golden cases. This proves orchestration, clarification/refusal, tool trajectory, evidence selection, citation plumbing, and structured plan validation for the curated agent fixture.

Key metrics:

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

### Live Retrieval 96-Case Baseline

The live retrieval run also passed all 96 golden cases, with 4 retrieval fallback events. These were DashScope rerank connection resets that fell back to the deterministic fused/domain-ranked result path without failing the agent response.

Interpretation:

- Live provider access and the local `thinkpad_m4` index are usable at agent scale.
- Provider fallback paths are exercised in reality, not only mocks.
- The result should not be read as final retrieval quality for all possible technician questions; it is a 96-case golden baseline.

### Live LLM 96-Case Baseline

The live LLM run evaluated all 96 cases. Only 36 cases required LLM composition; the other cases still exercised agent orchestration and validation. The run produced 5 failures.

Failed cases:

| Case | Category | Failure Type |
|---|---|---|
| `m8_fru_thinkpad_t480_hmm_1010` | FRU procedure | provider/LLM validation error |
| `m8_fru_thinkpad_t490_hmm_1020` | FRU procedure | provider/LLM validation error |
| `m8_fru_thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm_1030` | FRU procedure | provider/LLM validation error |
| `m8_fru_thinkpad_p1_gen4_x1_extreme_gen4_hmm_1010` | FRU procedure | provider/LLM validation error |
| `m8_chain_thinkpad_t480_hmm_1020` | Dependency-chain plan | provider/LLM validation error |

Important metrics:

| Metric | Value |
|---|---:|
| `llm_citation_preservation` | 0.8611 |
| `provider_error_rate` | 0.0521 |
| `unsupported_claim_rate` | 0.0521 |
| `citation_accuracy` | 1.0000 |
| `required_tool_coverage` | 1.0000 |

Interpretation:

- The evidence pipeline remained complete; the failures belong to live LLM composition/provider behavior.
- M8 should not claim perfect generated-answer quality.
- The next remediation should tighten LLM retry, output schema validation, and composer prompt/repair logic before exposing an agent MCP tool.

### Stress Benchmark

Generated local stress fixture: ignored `data/eval/m8_agent_stress_candidates.json`.

The stress generator sampled 194 cases from M3 extraction artifacts:

| Stress Category | Cases |
|---|---:|
| `stress_error_code` | 64 |
| `stress_fru_procedure` | 64 |
| `stress_screw_spec` | 50 |
| `stress_safety` | 8 |
| `stress_diagram` | 8 |

Stress failures are not gold accuracy failures because the stress set is generated from extraction candidates, not human-reviewed truth. They are still useful pressure tests.

Observed stress findings:

- Some diagnostic table rows look like FRU IDs, for example `2201`, `2204`, and `2205`, and should be filtered before being treated as procedure targets.
- Some component aliases from extracted HMM labels are not yet normalized into the agent component detector.
- Live retrieval did not change the stress failure count, but improved citation/identifier coverage among successful cases.

## What The Metrics Mean

The M8 results separate three different claims:

| Claim | Evidence | Status |
|---|---|---|
| Evidence tool accuracy | M7 structured/live tool eval | Clean for current golden set |
| Agent trajectory accuracy | M8 deterministic/live retrieval 96-case eval | Clean for current golden set |
| Generated repair-plan faithfulness | M8 live LLM 96-case eval | Not clean; 5 failures recorded |

This is the correct boundary: an evidence tool score of 1.0 does not imply a generated repair plan score of 1.0.

## Follow-Up Remediation

Recommended next work before or during M9:

1. Add LLM composition retry with a cheaper validation-only repair pass.
2. Add stricter structured JSON output mode for the composer where provider support permits.
3. Split stress candidate generation into gold-candidate review and non-gold pressure tests.
4. Add alias normalization for HMM component labels found in stress failures.
5. Add a short demo script using deterministic mode first and live LLM mode second, explicitly showing the validation layer.
