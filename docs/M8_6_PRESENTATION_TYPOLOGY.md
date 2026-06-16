# M8.6 Research: HMM Procedure Presentation Typology

Date: 2026-06-16
Status: research complete AND remediation implemented (M8.6). See the
"Implementation outcome" section at the end and `docs/IMPLEMENTATION_LOG.md`.
Method: read-only layout analysis of all 8 local HMM PDFs via
`scripts/thinkpad_presentation_typology.py` (counts vector `get_drawings` and
embedded `get_images` per page; walks each "Removal steps of ..." header to the
next FRU heading; classifies by text-step count vs figure density). No manual
prose is committed.

## Why this research exists

M8.5b human annotation (user opened the real PDFs) found that FRU 1070 thermal
fan and FRU 1030 M.2 SSD removal procedures are exploded-view **images** with no
textual steps. The extractor had emitted nearby unrelated prose (X-Rite color
calibration, FCC-panel notes, screw tables, `When installing` blocks) as if it
were the removal procedure. The user asked to first understand, across the whole
corpus, what presentation types exist for queries that must produce steps, before
changing any code. This document is that typology.

## Headline finding

216 "Removal steps of ..." sections across 8 manuals:

| Presentation type | Count | Share |
|---|---:|---:|
| IMAGE_ONLY (steps are in the figure; section text is a screw table, `When installing` note, or unrelated note) | 197 | 91% |
| INTERLEAVED (text steps interleaved among figures) | 19 | 9% |
| TEXT_ONLY (textual steps, no figure) | 0 | 0% |

Every manual is consistent: IMAGE_ONLY dominates in all 8. No manual has any
TEXT_ONLY removal procedure.

**Implication:** extracting removal steps from text is physically impossible for
~91% of FRUs, because the steps are not in the text. Any text-driven step
extractor must either fabricate steps (pull adjacent unrelated prose) or be empty
for these sections. This is the root cause of the M8.5 step-citation gold
failure, and of the runtime `get_fru_procedure` returning misattributed steps.

## The INTERLEAVED 9% is not uniformly real removal text

Of the 19 INTERLEAVED sections, only about half carry genuine removal-action
text; the rest are IMAGE_ONLY procedures whose only text happens to be a numbered
non-removal block:

Genuine interleaved removal text (worth fixing extraction so steps are not dropped):
- LCD panel / elastic adhesive tape removal: t14g2 p112/115/117, t14g3 p94,
  t490 p100, e14 p90/92 (Grasp tapes / Lift panel / Detach LCD cable).
- Wireless-LAN antenna assembly: t14g2 p124, t490 p107, e14 p100/101
  (Release antenna cables / Remove assembly).
- Base cover: t480 p72 (Remove connector cover / Loosen screws / Press locations).
- Keyboard: t480 p81 — extractor captured only step 1 (Loosen screws) and DROPPED
  steps 2-4 ("Turn the computer over...", "Pivot the keyboard...", "Put the
  keyboard on the palm rest and detach the connectors. Then remove the keyboard"),
  which are interleaved between figures on p82-p83. Confirmed dropped-step defect.

Non-removal text misclassified as steps (these are really IMAGE_ONLY):
- t14g2 p77 M.2 SSD: "Make sure the computer is connected to the Internet" /
  "Open the pre-installed X-Rite Color Assistant app" (color calibration).
- t14g2 p99 system board: UEFI BIOS settings ("Enter the UEFI BIOS menu" / "select
  Linux"), not a removal action.
- p1_gen4 p67 base cover: "Install miscellaneous parts..." (install guidance).
- t480 p75 / p1_gen4 p70 memory: "pivot it downward until it snaps into place"
  (install-side continuation fragment).

So even within the 9%, reliable textual removal steps are concentrated in LCD
panel tape removal + antenna assembly + a few base cover / keyboard sections —
likely fewer than ~10 FRUs corpus-wide.

## Two confirmed runtime failure modes

1. WRONG (IMAGE_ONLY, 91%): the operation is in the figure; the extractor and
   `get_fru_procedure` return adjacent unrelated prose as steps (X-Rite, FCC-panel
   notes, screw tables, `When installing`). Verified on FRU 1030 SSD and 1070 fan.
2. MISSING (INTERLEAVED, 9%): the operation text is interleaved between figures;
   the extractor drops steps. Verified on T480 keyboard (3 of 4 steps captured,
   step 4 dropped). Root cause includes removal verbs not in the step-start
   vocabulary ("put", "turn", "pivot" handling) and line continuation/boundary
   handling across page and figure breaks.

## Required handling per type (design target, not yet implemented)

- IMAGE_ONLY (91%): do NOT synthesize steps from section text. Return the removal
  **figure(s)** plus structured truth that genuinely belongs to the FRU (screw /
  torque table rows), with an explicit statement that detailed steps are in the
  diagram and the section has no independent textual steps. This requires figures
  to carry a structured FRU attribution (`related_fru_id`), which today is None for
  all 1285 figure records (see `docs/POST_M8_5_IMAGE_TEXT_DEFECTS.md`).
- INTERLEAVED (9%): fix text extraction to capture ALL interleaved removal steps
  without dropping or merging across figure/page breaks, and without pulling in
  non-removal numbered blocks (BIOS/X-Rite/install).
- The existing `step_kind` classifier (M8.5b salvage) already separates
  removal_step from install_note/spec_table/warning at the record level and is the
  foundation for both behaviors.

## Scope note

This typology also bears on figures, warnings, and tables (see
`docs/POST_M8_5_IMAGE_TEXT_DEFECTS.md`): the figure-attribution gap is now on the
critical path because IMAGE_ONLY is the majority case and its correct answer is "a
figure". M8.6 remediation scope (steps-only vs steps+figures+warnings+tables) is a
pending user decision.

## Implementation outcome (M8.6, 2026-06-16)

User confirmed scope: fix the two existing step-producing query types
(fru_procedure, fru_dependency_chain); image_only acceptance = return the correct
removal figure + screw rows + an explicit "steps are in the diagram" signal, with
NO fabricated text steps (LLM-reads-image deferred to M8.7 using qwen-vl). The
three POST_M8_5 defects (image-only steps, warning false positives, table parent)
were fixed together.

Regenerated corpus (`data/extracted/m3`, gitignored) after implementation:

| Metric | Value |
|---|---|
| FRU procedures | 213 |
| presentation_type | image_only 194, interleaved 11, cross_ref 6, text_only 2 |
| variant-split procedures (Intel/AMD/type suffix) | 35 |
| figures attributed to a FRU (`related_fru_id`) | 975 / 1285 (75%) |
| procedures carrying `related_image_ids` | 198 / 213 |
| warnings total | 299 (was 679) |
| warning levels | CAUTION 131, SAFETY_RELATED 108, DANGER 60 (all 60 DANGER preserved) |

Verified runtime behavior on real data:
- FRU 1030 (M.2 SSD) and 1070 (thermal fan): now image_only, return the removal
  diagram + screw rows, no fabricated X-Rite / thermal-grease steps.
- FRU 1090 (T480 keyboard): interleaved, all 4 steps captured (the previously
  dropped "Put the keyboard on the palm rest..." step on page 83 is restored).
- thermal fan with Intel/AMD variants: split into two procedures.

Regression: 120-case deterministic strict and M8.4 human-gold (18) deterministic
both pass with 0 failures and all contract metrics at 1.0; dependency-chain
trajectories unaffected (trajectory_tool_sequence_accuracy = 1.0). The 1.0 results
are contract-fixture results, not open-world accuracy.

Acceptance caveat: for the 90% image_only majority, "correct steps" means the
correct removal diagram is returned and no steps are fabricated — not textual
step matching. Textual step reconstruction from diagrams is M8.7 (qwen-vl), which
depends on the figure attribution and an image-writing path added here.
