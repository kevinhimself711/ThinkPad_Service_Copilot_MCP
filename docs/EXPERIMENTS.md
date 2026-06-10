# Experiments

> Experiment log for ThinkPad Service Copilot MCP. Do not record full copyrighted manual text here.

## M1-001: Official Lenovo HMM Discovery

- Date: 2026-06-08
- Hypothesis: The 8 MVP ThinkPad HMM PDFs can be discovered automatically from official Lenovo support pages.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_discover_manuals.py --target-set m1 --output data\manifests\manuals_manifest.yaml
```

- Result: Passed. All 8 HMM PDF URLs were discovered through Lenovo product self-repair pages and `api/v4/contents/recommendmanual`.
- Failure notes: `productcontentslist` and `productmultlanguagelist` returned empty lists for the tested PID forms, so they are not primary discovery sources.
- Decision: Use product self-repair page GUID extraction plus `recommendmanual` as the M1 discovery path.

## M1-002: Local PDF Download Integrity

- Date: 2026-06-08
- Hypothesis: Official PDFs can be downloaded locally under ignored `data/manuals/` and recorded with SHA256.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_download_manuals.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\manuals --update-manifest data\manifests\manuals_manifest.yaml
```

- Result: Passed after adding integrity checks. 8 PDFs downloaded, total local size 416,466,848 bytes.
- Failure notes: Large Lenovo downloads initially completed early and produced partial PDFs. The downloader now checks remote `Content-Length` and resumes incomplete files with HTTP Range requests.
- Decision: Keep size and checksum validation mandatory before any local inspection or ingestion.

## M1-003: Upstream Ingest Dry Run

- Date: 2026-06-08
- Hypothesis: The upstream ingestion CLI can discover the local M1 PDFs without running full upsert.
- Command:

```powershell
.\.venv\Scripts\python scripts\ingest.py --path data\manuals --collection thinkpad_spike --dry-run
```

- Result: Passed. The CLI found 8 PDF files and exited without processing.
- Decision: Preserve upstream ingestion CLI and add ThinkPad-specific ingestion logic around it later.

## M1-004: Full PDF Structure Scan

- Date: 2026-06-08
- Hypothesis: PyMuPDF can provide enough structural signals to decide M2/M3 parser priorities.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_spike_inspect.py --manifest data\manifests\manuals_manifest.yaml --output data\extracted\m1_spike_summary.json
```

- Result: Passed. Full scan covered 877 pages across 8 manuals.
- Metrics:
  - Table candidates: 768.
  - PyMuPDF structured table candidates: 331.
  - Figure candidates: 773.
  - Raster fallback pages: 591.
  - FRU section candidates: 555.
  - Safety markers: 687.
- Failure notes: PyMuPDF emitted a suggestion to use `pymupdf_layout` for better layout analysis. M1 does not add that dependency yet.
- Decision: M2/M3 must implement exact table-record and FRU-section fixtures before generating authoritative answers.

## M1-005: Synthetic Domain Unit Tests

- Date: 2026-06-08
- Hypothesis: The new M1 manifest/discovery/parser contracts can be tested without live Lenovo calls or copyrighted text fixtures.
- Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

- Result: Passed, 10 tests.
- Failure notes: Initial FRU parser tests exposed two bugs: prerequisite FRU rows were misread as headings, and comma-separated FRU references were greedily merged. Both were fixed.
- Decision: Keep synthetic fixtures as the default for parser regression tests.

## M2-001: Domain Schema And Resolver Contracts

- Date: 2026-06-09
- Hypothesis: The M2 domain records, manifest validator, and model resolver can be tested with synthetic metadata only, without live Lenovo calls or copyrighted manual text.
- Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

- Result: Passed, 28 tests.
- Coverage:
  - Manifest accepts the committed M1 example with 877 total pages.
  - Manifest rejects non-Lenovo URLs, absolute or out-of-scope local paths, invalid checksums, duplicate manual IDs, and incomplete downloaded/validated statuses.
  - Citation-backed records serialize to JSON-safe dictionaries and reject missing grounding fields.
  - Resolver handles exact machine type, exact model+generation, compact generation aliases, ordinal generation aliases, generationless ambiguity, and unsupported models.
- Decision: M2 should stay as an internal Python domain API. Retrieval, MCP tools, vector stores, and generated repair answers remain out of scope until later milestones.

## M3-001: Synthetic Extraction Unit Tests

- Date: 2026-06-10
- Hypothesis: HMM extraction modules can preserve table rows, FRU prerequisites, figure fallback signals, safety citations, and CLI summary structure using synthetic fixtures only.
- Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

- Result: Passed, 36 tests.
- Coverage:
  - `HMMPage` and `ExtractionResult` serialization.
  - Table row/column preservation for exact error-code and screw-spec strings.
  - Markdown/text table fallback parsing.
  - FRU section boundaries and prerequisite dependency edges.
  - Guard against misclassifying numeric error-code rows such as `0271` as FRU procedures.
  - Raster fallback figure records without writing image files.
  - DANGER/CAUTION/safety-related warning records with citations.
  - CLI summary and JSONL output using a synthetic local PDF fixture.
- Decision: Synthetic extraction tests are sufficient for M3 regression coverage, but not enough to claim production-quality extraction over real HMMs.

## M3-002: Local Manifest Smoke Extraction

- Date: 2026-06-10
- Hypothesis: The M3 CLI can loop over the local 8-manual manifest and write all expected artifact files without requiring a full scan.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_extract_hmm.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\extracted\m3_smoke --max-pages 5
```

- Result: Passed. All 8 manuals were selected and processed with 5 pages each.
- Metrics:
  - Manuals succeeded: 8.
  - Manuals failed: 0.
  - Pages processed: 40.
- Decision: Keep `--max-pages` as the default local debugging path for quick CLI checks.

## M3-003: Full Local HMM Extraction

- Date: 2026-06-10
- Hypothesis: The M3 extraction layer can process all 8 local M1 PDFs and write ignored structured artifacts without changing upstream ingestion or vector stores.
- Command:

```powershell
.\.venv\Scripts\python scripts\thinkpad_extract_hmm.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\extracted\m3
```

- Result: Passed after adding lightweight table-probing gates around PyMuPDF `find_tables()`.
- Runtime: 665.57 seconds on the local Windows environment.
- Metrics from `data/extracted/m3/summary.json`:
  - Manuals requested: 8.
  - Manuals succeeded: 8.
  - Manuals failed: 0.
  - Pages: 877.
  - Table records: 797.
  - Figure records: 1285.
  - FRU procedures: 195.
  - Dependency edges: 535.
  - Warning records: 687.
- Output files:
  - `data/extracted/m3/tables.jsonl`
  - `data/extracted/m3/figures.jsonl`
  - `data/extracted/m3/fru_procedures.jsonl`
  - `data/extracted/m3/warnings.jsonl`
  - `data/extracted/m3/dependency_edges.jsonl`
  - `data/extracted/m3/summary.json`
- Failure notes: The first full run exceeded a 5-minute tool timeout while probing tables too broadly. `hmm_loader.py` was adjusted to call PyMuPDF `find_tables()` only on likely table pages; the full run then completed successfully.
- Interpretation notes: M3 figure records count embedded image candidates and raster fallback metadata; it is not directly comparable to the M1 figure-candidate metric and does not imply caption quality.
- Decision: M4 can consume M3 JSONL candidates for retrieval/rerank experiments, but exact-answer claims still require targeted quality review of representative table, figure, and FRU samples.
