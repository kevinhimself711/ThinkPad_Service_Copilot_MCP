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
