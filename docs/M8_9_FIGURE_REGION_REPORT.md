# M8.9 Figure-Region Cropping Report

Date: 2026-06-17

## Summary

M8.9 implemented sub-page figure-region metadata and rendering for image-only
ThinkPad HMM procedures. The milestone produced a real coverage improvement, but
did **not** meet the planned figure-correctness target.

Key result:

- `image_only` procedures with at least one image improved from 163/194 (84%) in
  M8.8 to 186/194 (96%) after M8.9 extraction.
- New figure records include 135 `region_crop` candidates.
- Final full live eval: 147/167 figure-correct, or 88%, with 167/167 non-empty
  reconstructions and 0 spec leaks.
- Targeted region eval: 82/91 figure-correct, or 90%, with 0 spec leaks.

This means M8.9 is useful as an evidence coverage improvement, but not sufficient
to claim the figure-correctness problem is solved. M9 should not present diagram
selection as >93% accurate unless a later remediation improves it.

## Implementation Facts

- `FigureRecord` now carries optional `figure_kind` and `source_image_id`.
- Extracted figures are typed as `embedded_image`, `page_raster`, or
  `region_crop`.
- Region crop records reuse `bbox` as a PDF page-coordinate crop rectangle.
- Region crops are generated from FRU heading y-bands, drawing bands, page
  dimensions, and continuation-page logic.
- Diagnostic pseudo-FRUs such as UUID/error rows are excluded from region crop
  generation.
- qwen-vl rendering clips only `region_crop` figures. Embedded-image bboxes are
  not clipped because the initial live run showed that clipping embedded images
  destroyed context and regressed figure naming.
- Native `embedded_image` and `page_raster` evidence remains ahead of
  `region_crop` in `related_image_ids`; region crops are retained as additional
  evidence and recovery candidates, not unconditional first-choice evidence.

## Live Evaluation

| Run | Population | Correct | Rate | Non-empty | Spec leaks | Notes |
|---|---:|---:|---:|---:|---:|---|
| M8.8 baseline | 148 | 133 | 89% | 148/148 | 0 | Within-page y-position attribution |
| M8.9 full, first crop-first attempt | 167 | 97 | 58% | 166/167 | 0 | Regressed because embedded-image bbox was clipped and region crops displaced stable figures |
| M8.9 full, clip fix only | 167 | 134 | 80% | 167/167 | 0 | Embedded images no longer clipped |
| M8.9 final full | 167 | 147 | 88% | 167/167 | 0 | Native figures prioritized, region crops retained |
| M8.9 final targeted regions | 91 | 82 | 90% | 91/91 | 0 | Region-linked image-only procedures |

The final full rate is lower than the M8.8 percentage, but the population is not
like-for-like: M8.9 evaluates 167 procedures instead of 148 because region crops
recover many procedures that previously had no image. Correct count increased
from 133 to 147, while zero-image `image_only` procedures dropped from 31 to 8.

## Remaining Failures

Final full live eval has 20 mismatches:

- 12 fine-grained component-name mismatches where the diagram is a local part but
  qwen-vl names an adjacent or broader component.
- 4 neighbor large-assembly mismatches such as bottom cover, display assembly, or
  keyboard.
- 4 neighbor battery / large-part mismatches.

Representative failures include system board seen as keyboard, I/O bracket seen
as wireless WAN card, coin-cell battery seen as speaker assembly, pen charger or
holder seen as nearby internal components, and memory shield seen as M.2 SSD.

These failures suggest that vertical crop regions alone are not enough. The next
quality step should combine region crops with one of:

- x/y connected-component crop extraction rather than full-width vertical bands;
- figure-number or callout proximity;
- a stricter vision naming prompt that distinguishes part vs nearby context;
- human-reviewed crop gold for the remaining failure cluster.

## Regression

- Focused tests: 56 passed.
- Full ThinkPad non-LLM suite: 145 passed.
- 120-case deterministic strict regression: 120 cases, 0 failed, pass rate 1.0.
- Ruff: all checked files passed.
- `git diff --check`: passed with only Git CRLF conversion warnings.

## Decision

M8.9 should be recorded as **complete with risk**, not as a clean quality gate.
It materially improves coverage and preserves 0 spec leaks, but it misses the
planned >93% figure-correctness target. M9 packaging can proceed only if it
explicitly presents this boundary; otherwise a follow-up M8.10 should target the
remaining crop precision problem before packaging.
