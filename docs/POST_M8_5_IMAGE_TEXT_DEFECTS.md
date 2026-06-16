# Post-M8.5 Required Defect Remediation: Image-Priority Content vs Nearby-Text Leakage

Date opened: 2026-06-16
Status: RESOLVED in M8.6 (2026-06-16). All three defects below were remediated;
see `docs/M8_6_PRESENTATION_TYPOLOGY.md` and `docs/IMPLEMENTATION_LOG.md` (M8.6)
for the implementation. This document is retained as the record of the defect
that drove the M8.6 pivot.

## Resolution summary (M8.6)

- Image-only procedures: `FRUProcedure.presentation_type` now classifies each
  procedure (image_only / interleaved / cross_ref / text_only). `get_fru_procedure`
  returns the attributed removal figure + screw/torque rows + `steps_in_diagram`
  for image_only, and the agent emits a "Refer to cited removal diagram" step
  instead of fabricating steps. Corpus: 194/213 procedures are image_only.
- Figure attribution: `attribute_figures_to_procedures` now sets
  `related_fru_id` / `related_component` from the owning FRU section's page span.
  975/1285 figures attributed (was 0); 198/213 procedures carry related_image_ids.
- Warning false positives: `safety.py` now gates emission on a real trigger
  (DANGER/CAUTION/Attention/imperative). Warnings dropped 679 -> 299; SAFETY_RELATED
  460 -> 108; all 60 genuine DANGER blocks preserved.
- Table parent mis-attribution: `_find_parent_section_for_table` attributes each
  table to the nearest preceding FRU heading (first-heading fallback, not last).

## Why this exists

During M8.5b human annotation, the user opened the actual PDFs and found that the
ThinkPad HMM "Removal steps of the thermal fan assembly" (FRU 1070) is an
exploded-view **image** with no numbered text steps. The extractor had emitted the
adjacent `When installing:` block as if it were the removal procedure. That is a
direct violation of AGENTS.md section 6.4 (diagrams are retrieval targets, not step
sources) and section 6.1 (citations must be real).

M8.5b fixed this for FRU procedure steps via `step_kind` classification
(`removal_step` / `install_note` / `spec_table` / `warning` / `image_only_marker` /
`other`) so install/table/warning text can no longer masquerade as a removal step.

The user then asked for a systemic audit: is the same "image-priority content
described by nearby unrelated text" pathology present elsewhere? A read-only audit of
the regenerated `data/extracted/m3/*` artifacts confirms it is. The findings below are
NOT yet fixed; they are deferred to a dedicated remediation milestone after M8.5b.

## Audit findings (read-only, on regenerated M8.5b extraction)

Corpus: figures=1285, tables=797, warnings=679, fru_procedures=195.

### Severity HIGH — Figures have no structured FRU attribution

- `related_fru_id` is `None` for **1285 / 1285** figure records.
- `related_component` is `None` for all of them.
- `caption` is always a placeholder (`"Embedded HMM image candidate"` or
  `"Raster fallback candidate for vector line drawing"`).
- `surrounding_text` is the **whole page text** of the figure's own page.
- Consequence: `get_related_diagram` can only match a figure when the queried
  component string happens to appear in that page's prose. A page that carries
  several FRU sections (e.g. 1060 / 1070 / 1080 headings plus a screw table plus a
  `When installing` block) yields figures whose only "context" is that mixed prose.
  There is no guarantee the returned figure is the removal diagram for the queried
  FRU, and no structured link from figure to FRU. This is the same class of defect as
  the thermal-fan removal step.

### Severity HIGH — Warnings are keyword hits, not real warning blocks

- `src/thinkpad/safety.py` matches bare tokens
  `\b(DANGER|CAUTION|Attention|ESD|battery|batteries|system board)\b`.
- Warning levels: SAFETY_RELATED=460, CAUTION=159, DANGER=60.
- **402 / 460** SAFETY_RELATED records have NO `DANGER` / `CAUTION` / `Attention` /
  imperative (`MUST` / `DO NOT`) anywhere in their captured context — they are
  incidental occurrences of the words "battery" or "system board" in ordinary prose
  (e.g. "disconnect the battery connector").
- Consequence: `get_safety_warnings` returns a large volume of false-positive
  "warnings", violating section 6.6 (safety warnings must be real) and burying the
  60 genuine DANGER blocks in noise.

### Severity MEDIUM — Table parent-section can be mis-attributed

- `table_extractor._find_parent_section` takes the **last** FRU heading on the page.
- 528 / 797 table rows have NO `parent_section` at all.
- On pages spanning multiple FRU sections, a screw/torque table belonging to an
  earlier FRU on the page is attributed to the last heading. 62 tables carry
  torque/screw columns and feed `get_screw_spec`; mis-attribution returns the wrong
  FRU's torque/screw spec.

## Common root cause

Extraction of image-priority content (figures, tables, warnings, and image-only
removal procedures) relies on a "nearby page text" heuristic rather than a structured
decision about which FRU the content belongs to, whether a warning is a real
DANGER/CAUTION block, and whether a removal procedure even has textual steps. The FRU
removal-step case was fixed in M8.5b; the figure, warning, and table cases remain.

## Required remediation (after M8.5b)

1. Figures: derive `related_fru_id` / `related_component` from the FRU section the
   figure sits within (section-bounded, not whole-page), and stop using whole-page
   prose as the only retrieval signal. Make `get_related_diagram` prefer figures whose
   structured FRU attribution matches the resolved model + component.
2. Warnings: require a real warning trigger (`DANGER` / `CAUTION` / `Attention` /
   `WARNING` heading or an explicit imperative safety clause) before emitting a
   `WarningRecord`; demote bare-keyword occurrences. Preserve the 60 genuine DANGER
   blocks and re-test against known warning pages.
3. Tables: attribute each table to the nearest **preceding** FRU heading by text
   offset rather than the last heading on the page; add tests for multi-FRU pages.
4. Add regression tests mirroring `test_image_only_removal_yields_no_removal_step`
   for each content type.

## Scope boundary

This work is intentionally OUT of M8.5b scope to keep the step-citation human-gold
milestone focused. M8.5b records this defect set so it is not lost. Do not expose the
affected tools as authoritative in any demo path until remediated.
