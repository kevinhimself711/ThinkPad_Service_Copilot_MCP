# M8.5 Step-Level Citation Report

## Status

M8.5a is complete. M8.5b is intentionally blocked on human annotation.

M8.5a implements the technical prerequisites for step-level human gold:

- FRU extraction now emits `step_records` with per-step citations.
- `get_fru_procedure` returns those `step_records`.
- The repair-planning agent uses step-level citations when available.
- The agent records `procedure_level_citation_fallback_rate`.
- The evaluator accepts optional `expected.step_pages` and reports step-page metrics.
- A local ignored review pack was generated for human step-page annotation.

No formal M8.5 human step-gold fixture exists yet. No M8.5 live baseline has been run yet. Those belong to M8.5b after human review.

## Why M8.5 Exists

M8.4 proved that human page review is valuable, but the FRU procedure page metric still had a structural weakness: every generated repair step copied the same procedure-level citation. Under that data shape, a per-step page metric cannot produce partial credit. A case either hits the broad procedure page range for every step or misses it for every step.

M8.5a fixes the data path so future human gold can test step-level page truth instead of only procedure-level page truth.

## M8.5a Artifacts

Committed code and tests:

- `src/thinkpad/models.py`: added `FRUStepRecord` and `FRUProcedure.step_records`.
- `src/thinkpad/fru_extractor.py`: maps extracted FRU step lines to page numbers using page offsets.
- `src/thinkpad/tool_service.py`: returns `step_records` from `get_fru_procedure`.
- `src/thinkpad/agent.py`: prefers step-level FRU citations and reports fallback rate.
- `src/thinkpad/agent_evaluation.py`: supports `expected.step_pages`.
- `scripts/thinkpad_prepare_step_citation_review.py`: generates the local human review pack.

Ignored local outputs:

- `data/extracted/m3/fru_procedures.jsonl`: regenerated with step records.
- `data/eval/m8_5_step_citation_review.json`
- `data/eval/m8_5_step_citation_review.md`

Review pack summary:

| Metric | Value |
|---|---:|
| FRU procedures extracted | 195 |
| Procedures with `step_records` | 157 |
| Procedures with multiple step pages | 92 |
| Review candidates generated | 12 |
| Multi-page review candidates | 7 |
| Manuals covered | 8 |

## Human Annotation Instructions

Open `data/eval/m8_5_step_citation_review.md`.

For each candidate:

- Open the listed local PDF.
- Check whether the FRU procedure and listed step labels are real reviewable steps.
- Set case `Review status` to `verified`, `corrected`, or `rejected`.
- For each step, set `Review status` to `verified`, `corrected`, or `not_applicable`.
- If candidate page is correct, put the same page in `Verified page`.
- If candidate page is wrong, put the true page in `Verified page`.
- If a step is a heading, broken OCR fragment, table residue, or otherwise not useful, mark it `not_applicable`.
- Do not copy Lenovo manual prose into notes.

Human gold must record true pages only. Wrong-page adversarial tests stay synthetic and are not human gold.

## M8.5b Gate

After human review, M8.5b should:

1. Finalize verified/corrected step annotations into `tests/fixtures/thinkpad_m8_5_step_citation_gold_set.json`.
2. Reject pending or unreviewed cases.
3. Preserve rejected/not-applicable counts in an audit artifact.
4. Run deterministic strict, live retrieval strict, and raw live LLM strict baselines.
5. Re-run M8.4 human gold and 120-case regression baselines.

M9 should not start until M8.5b confirms that step-level citation metrics have real discriminability on human-reviewed cases.
