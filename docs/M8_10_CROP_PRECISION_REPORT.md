# M8.10 Crop Precision Remediation Report

Date: 2026-06-18

## Summary

M8.10 implemented figure-selection diagnostics and an additional precise crop
candidate path, but it did **not** improve live figure correctness over M8.9.

Final decision:

- Keep the safe M8.9-style primary behavior: native `embedded_image` /
  `page_raster` evidence remains first; `region_crop` and
  `region_crop_precise` are retained as additional diagnostic/recovery evidence.
- Do not claim M8.10 met the planned `>=93%` gate.
- Do not enter M9 as a clean quality pass. Either accept the M8.9/M8.10 88%
  full-live figure boundary explicitly, or run M8.11 focused on residual visual
  ownership.

## Implementation Facts

- `HMMPage` now preserves `drawing_rects` in addition to legacy
  `drawing_bands`.
- The HMM loader records PyMuPDF drawing rectangles so later stages can reason
  about x/y drawing clusters, not only vertical y-bands.
- `FigureRecord.figure_kind` now allows `region_crop_precise`.
- FRU attribution now generates:
  - stable `region_crop` records using the M8.9 full-width vertical crop; and
  - additional `region_crop_precise` records using connected drawing-rect
    clusters.
- qwen-vl rendering clips both `region_crop` and `region_crop_precise`.
- `scripts/thinkpad_vision_live_eval.py` now records primary-image diagnostics:
  primary image id, kind, page, bbox, source image id, selection score/reason,
  related image ids, and whether the row belongs to the M8.9 failure set.
- The live evaluator keeps the M8.8/M8.9 name-match scorer unchanged. A bug in
  M8.10's first eval attempt was fixed so diagnostic `region_crop_precise`
  records do not reduce the M8.9-compatible eligible population.
- `scripts/thinkpad_prepare_crop_review.py` generates a local ignored residual
  crop review pack for the old mismatch set, targeted-region mismatches, and
  zero-image image-only procedures.

## Extraction Results

Local ignored extraction was regenerated under `data/extracted/m3`.

| Metric | M8.9 | M8.10 |
|---|---:|---:|
| Figure records | 1420 | 1550 |
| Embedded-image figures | 694 | 694 |
| Page-raster figures | 591 | 591 |
| Region-crop figures | 135 | 135 |
| Precise region-crop figures | 0 | 130 |
| FRU procedures | 213 | 213 |
| Image-only procedures | 194 | 194 |
| Image-only procedures with images | 186 | 186 |
| Image-only procedures with no image | 8 | 8 |
| Image-only procedures with region-linked images | 98 | 98 |

M8.10 preserved M8.9 image coverage, but did not improve coverage.

## Live Evaluation

All live runs used the same qwen-vl name-check scorer as M8.8/M8.9. The scorer
was not relaxed.

| Run | Population | Correct | Rate | Non-empty | Spec leaks | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| M8.9 final full baseline | 167 | 147 | 88% | 167/167 | 0 | Baseline before M8.10 |
| M8.10 smoke | 10 | n/a | n/a | 10/10 | 0 | Provider reachable; guard held |
| M8.10 experimental selector full | 167 | 135 | 80% | 166/167 | 0 | Regressed; region promotion displaced stable native evidence |
| M8.10 final old-failure target | 20 | 0 | 0% | 20/20 | 0 | Old M8.9 failures remain unresolved |
| M8.10 final targeted regions | 91 | 82 | 90% | 91/91 | 0 | Same as M8.9 targeted region result |
| M8.10 final full stable | 167 | 147 | 88% | 167/167 | 0 | Same as M8.9 final full result |

M8.10 did not meet the planned `>=93%` figure-correctness gate. The failed
selector attempt is important evidence: naively promoting region crops as primary
evidence makes the result worse, not better.

## Root Cause

M8.9 and M8.10 both solve "does this procedure have an image?" for many
image-only FRUs. They do not yet solve fine-grained visual ownership inside a
shared exploded-view page.

Observed residual pattern:

- Old M8.9 residuals stayed residual: the final M8.10 old-failure target run was
  0/20.
- The precise drawing-cluster crop is not enough because many HMM drawings put
  the target small component beside or on top of a larger assembly. Removing page
  context can make qwen-vl name the adjacent large part; keeping page context can
  make it name the same adjacent large part.
- The primary selector cannot reliably infer the target component from metadata
  alone. Bbox geometry and FRU ids are necessary but not sufficient.
- The bottleneck remains evidence selection / visual ownership, not qwen-vl
  reconstruction or spec leakage. Final M8.10 still has 100% non-empty
  reconstructions and 0 spec leaks.

## Regression

| Check | Result |
|---|---|
| Focused figure/vision/model tests | 28 passed |
| Full ThinkPad non-LLM suite | 149 passed |
| 120-case deterministic strict regression | 120 cases, 0 failed, pass rate 1.0 |
| Ruff | Passed |

## Decision

M8.10 is complete as a diagnostic/remediation attempt, but not as a successful
quality gate. It preserves the M8.9 boundary and adds the artifacts needed to
debug the residual mismatch set, but it does not justify M9 as a clean quality
handoff.

Recommended next step: M8.11 residual visual ownership remediation.

M8.11 should not relax the live scorer. It should use human visual review of the
27-case residual crop pack to classify whether each failure is:

- wrong neighbor crop;
- correct crop but qwen-vl name-check false negative;
- ambiguous shared drawing;
- missing required crop;
- or extraction/ownership bug.

Only after that classification should the code change, likely by adding
figure-number / callout proximity or a small human-reviewed residual fixture
rather than more blind crop generation.
