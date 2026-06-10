# M1 Spike Report

> Date: 2026-06-08
> Phase: M1 risk-validation spike
> Corpus: 8 official Lenovo ThinkPad HMM PDFs, local-only.

## Summary

M1 successfully acquired and inspected 8 unique official Lenovo ThinkPad Hardware Maintenance Manual PDFs. The local corpus is 416,466,848 bytes and remains under ignored `data/manuals/`.

The spike confirms that the upstream framework can discover the PDFs via `scripts/ingest.py --dry-run`, but domain-specific ingestion is still required for tables, vector line drawings, FRU prerequisites, model metadata, and safety grounding.

Decision: proceed to M2. Do not start full-scale ingestion yet; first implement stable ThinkPad metadata and model-resolution contracts.

## Corpus

| Manual ID | Source PDF | Bytes | SHA256 |
|---|---|---:|---|
| `thinkpad_t14_gen2_p14s_gen2_hmm` | `t14_gen2_p14s_gen2_hmm_en.pdf` | 65,810,405 | `91f8c030f7b4d23a7b0ede4c26b3d3561bb69a2b2a5b647a9a2e466e39aace15` |
| `thinkpad_t14_gen3_p14s_gen3_hmm` | `t14_gen3_p14s_gen3_hmm_en.pdf` | 46,117,257 | `db019ff8aa4e2de21fa15d612f829f220079fa127a46558e39763e0926c1abbd` |
| `thinkpad_t480_hmm` | `t480_hmm_en.pdf` | 39,600,598 | `4cbe2f62aeb5b8acbd5b904143024f6312650ef0f8b9cb7857aecd0ba5e277f6` |
| `thinkpad_t490_hmm` | `t490_hmm_en.pdf` | 47,019,007 | `65bd368636910ce0221f9ceed51ac8ea76dddb7acb7604bb16f50e66cd024cd9` |
| `thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm` | `tp_x1_carbon_gen9_x1_yoga_gen6_hmm_en.pdf` | 81,807,489 | `370a2083e22d5b37d34b846d1182205e035ca689483532346456cca2a3fcb884` |
| `thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm` | `x1_carbon_gen10_x1_yoga_gen7_hmm_en.pdf` | 49,881,460 | `c7f2858a7ed3f55b0b61cbc4623193706bb56d01d7edbe13ac8e8d344e7b207d` |
| `thinkpad_e14_gen2_e15_gen2_hmm` | `e14_gen2_e15_gen2_hmm_en.pdf` | 41,685,849 | `753f99060a09e8d13255d140b30d0e990af7486212f5805d155a0a07017eff45` |
| `thinkpad_p1_gen4_x1_extreme_gen4_hmm` | `x1_extreme_gen4_p1_gen4_hmm_en.pdf` | 44,544,783 | `9e3a5858fd37b2503297f1cad60cb611a720a65b5c43eb18db1407f19262615a` |

Official discovery path:

1. Product self-repair page.
2. Product `Guid` plus `ParentGuids`.
3. Lenovo `api/v4/contents/recommendmanual`.
4. `hardwareMaintenanceManual.pdfs`.

The earlier `productcontentslist` and `productmultlanguagelist` attempts were not reliable for this use case, so they are not the primary discovery path.

## Full Scan Results

| Manual ID | Pages | Table Candidates | Figure Candidates | Raster Fallback Pages | FRU Sections | Safety Markers |
|---|---:|---:|---:|---:|---:|---:|
| `thinkpad_t14_gen2_p14s_gen2_hmm` | 133 | 126 | 120 | 109 | 82 | 90 |
| `thinkpad_t14_gen3_p14s_gen3_hmm` | 102 | 90 | 90 | 46 | 72 | 78 |
| `thinkpad_t480_hmm` | 114 | 101 | 104 | 73 | 78 | 108 |
| `thinkpad_t490_hmm` | 117 | 104 | 103 | 92 | 81 | 89 |
| `thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm` | 99 | 88 | 84 | 69 | 59 | 75 |
| `thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm` | 102 | 89 | 88 | 49 | 58 | 86 |
| `thinkpad_e14_gen2_e15_gen2_hmm` | 109 | 95 | 97 | 83 | 72 | 77 |
| `thinkpad_p1_gen4_x1_extreme_gen4_hmm` | 101 | 75 | 87 | 70 | 53 | 84 |
| Total | 877 | 768 | 773 | 591 | 555 | 687 |

Table-candidate breakdown:

- PyMuPDF structured table candidates: 331.
- Text heuristic candidates: 437.
- Candidate types: 158 error-code, 179 screw-spec, 233 FRU, 198 unknown.

## Risk Findings

R1 table extraction: high risk, validated. PyMuPDF can detect many table structures, but exact row/column preservation is not proven. M2/M3 must add table-record fixtures and exact lookup tests before any error code, screw spec, torque, or FRU table answer is trusted.

R2 figure extraction: high risk, validated. 591 pages show drawing signals where raster fallback is likely needed. Embedded image extraction alone will miss many vector line drawings.

R3 metadata extraction: manageable. The manifest plus title-page candidates are sufficient for M1. Model/generation ambiguity still requires a resolver in M2.

R4 FRU procedure chunking: high risk, validated. The spike found 555 FRU section candidates. Regex parsing is useful for reconnaissance but not reliable enough for final procedure answers without section-boundary and prerequisite-chain tests.

R5 safety warnings: high risk, validated. Safety markers are frequent enough that warning metadata should be first-class in future chunk/table/procedure records.

## Verification

Commands run:

```powershell
.\.venv\Scripts\python scripts\thinkpad_discover_manuals.py --target-set m1 --output data\manifests\manuals_manifest.yaml
.\.venv\Scripts\python scripts\thinkpad_download_manuals.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\manuals --update-manifest data\manifests\manuals_manifest.yaml
.\.venv\Scripts\python scripts\ingest.py --path data\manuals --collection thinkpad_spike --dry-run
.\.venv\Scripts\python scripts\thinkpad_spike_inspect.py --manifest data\manifests\manuals_manifest.yaml --output data\extracted\m1_spike_summary.json
.\.venv\Scripts\python -m pytest tests/thinkpad -q
```

The download step initially produced partial PDFs for several large files. The downloader was updated to compare remote `Content-Length`, reject incomplete files, and resume with HTTP Range requests.

## Next Decisions

- M2 should implement real ThinkPad domain models and manifest parsing as production modules.
- M2 should add model/generation resolver tests before retrieval work.
- M3 should replace spike table and FRU regex logic with tested parsers.
- Full ingestion should wait until table-row preservation, raster fallback, and prerequisite preservation are validated with synthetic fixtures and selected manual samples.
