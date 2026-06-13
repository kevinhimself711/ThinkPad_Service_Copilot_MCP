# M8.4a Human Gold Review Guide

M8.4a prepares a local review pack. It does not create the committed human gold set.

Generated local files:

- `data/eval/m8_4_human_gold_review.json`
- `data/eval/m8_4_human_gold_review.md`

Both files are ignored local artifacts. They should not be committed.

## Review Steps

1. Open `data/eval/m8_4_human_gold_review.md`.
2. For each candidate, open the listed `pdf_local_path`.
3. Check whether `candidate_pages` contain the cited FRU procedure, table row, warning, diagram, or dependency edge.
4. Edit the local JSON review pack:
   - `review_status`: use `verified`, `corrected`, or `rejected`.
   - `verified_pages`: use the confirmed HMM PDF page numbers.
   - `reviewer_notes`: keep this short and do not copy Lenovo manual prose.
5. Tell Codex when review is complete so M8.4b can convert verified cases into the committed human gold fixture.

## Rules

- Do not copy Lenovo manual paragraphs, tables, or diagram captions into the review pack.
- Do not mark a candidate as human gold unless a human checked the page against the PDF.
- Reject candidates that depend on ambiguous extraction artifacts or do not make a useful evaluation case.
- Negative cases do not need PDF pages; verify only that the expected status is the intended behavior.

## M8.4b Handoff

M8.4b should only consume candidates with:

- `review_status` set to `verified` or `corrected`.
- Non-empty `verified_pages` for positive citation-bearing cases.
- No copied manual prose in `reviewer_notes`.
