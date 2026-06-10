# ThinkPad Domain Developer Spec

> Version: M2 domain contract
> Date: 2026-06-09
> Scope: ThinkPad HMM corpus metadata, citation records, manifest validation, and conservative model resolution.

## 1. M1 Intent

M1 validates whether Lenovo ThinkPad Hardware Maintenance Manuals can be turned into a reliable domain corpus before building full ingestion, retrieval, MCP tools, or graph features.

M1 does not add ThinkPad MCP tools, vector indexes, full extracted text, image dumps, or generated answers. It only adds local corpus tooling and small parser probes that preserve upstream architecture.

## 2. Data Governance

Allowed in Git:

- Official Lenovo source URLs.
- Manifest examples and schema validation code.
- Discovery/download/inspection scripts.
- Aggregate spike counts and engineering decisions.
- Synthetic tests and synthetic parser fixtures.

Not allowed in Git:

- Lenovo HMM PDFs.
- Full extracted Markdown/text.
- Full image/page-render dumps.
- Vector stores or chunk stores containing manual text.
- Secrets or device serial numbers.

All real local artifacts stay under ignored paths:

- `data/manuals/`
- `data/manifests/`
- `data/extracted/`
- `data/images/`

## 3. Manifest Contract

The committed example manifest is `config/manuals_manifest.example.yaml`. Real manifests should be generated locally under `data/manifests/manuals_manifest.yaml`.

Required fields per manual:

- `manual_id`
- `title`
- `models`
- `generations`
- `machine_types`
- `source_type: lenovo_official`
- `source_url`
- `product_page_url`
- `local_pdf_path`
- `document_type: hmm`
- `language`

Optional M1 fields:

- `year`
- `edition`
- `page_count`
- `checksum_sha256`
- `file_size_bytes`
- `product_guids`
- `spike_status`
- `notes`

Validation rules:

- `source_url` and `product_page_url` must be official Lenovo URLs.
- `local_pdf_path` must be repo-relative and stay under `data/manuals/`.
- `checksum_sha256`, when present, must be a 64-character hex digest.
- `file_size_bytes`, when present, must be positive.
- `page_count`, when present, must be positive.
- `spike_status` must be `planned`, `discovered`, `downloaded`, or `validated`.
- `downloaded` and `validated` records require checksum, file size, and local path.
- `validated` records require page count.

## 4. M1 Tooling

Discovery:

```powershell
.\.venv\Scripts\python scripts\thinkpad_discover_manuals.py --target-set m1 --output data\manifests\manuals_manifest.yaml
```

The primary discovery path is:

1. Fetch the Lenovo product self-repair page.
2. Extract product `Guid` and `ParentGuids`.
3. Call Lenovo `api/v4/contents/recommendmanual`.
4. Select `hardwareMaintenanceManual.pdfs`.

Download:

```powershell
.\.venv\Scripts\python scripts\thinkpad_download_manuals.py --manifest data\manifests\manuals_manifest.yaml --output-dir data\manuals --update-manifest data\manifests\manuals_manifest.yaml
```

The downloader validates official Lenovo PDF URLs, compares remote `Content-Length`, supports HTTP Range resume, writes SHA256, and refuses output outside `data/manuals`.

Inspection:

```powershell
.\.venv\Scripts\python scripts\thinkpad_spike_inspect.py --manifest data\manifests\manuals_manifest.yaml --output data\extracted\m1_spike_summary.json
```

The inspector uses PyMuPDF and stores only aggregate structure signals:

- page count and text-bearing page count
- table candidates
- figure/drawing candidates
- raster fallback candidates
- FRU section candidates
- safety warning markers

No full manual text is stored in committed docs.

## 5. M2 Domain Schema Contract

M2 introduces internal Python records under `src/thinkpad/`. These records are not MCP tools yet.

Required domain records:

- `Citation`: required grounding fields `manual_id`, `source_url`, `page_start`, optional `page_end`, `section`, and `section_id`.
- `TableRecord`: one structured table row with preserved columns, row values, page, table type, parent section, and citation.
- `FigureRecord`: one diagram/image/page-render reference with page, optional bbox, caption, surrounding text, storage URI, and citation.
- `FRUProcedure`: procedure ID, FRU ID/name, steps, prerequisites, warnings, related image IDs, and citation.
- `WarningRecord`: safety marker with warning level, text, page, component hint, and citation.
- `DependencyEdge`: directed FRU prerequisite relation with citation.
- `ModelCandidate`: resolver candidate with canonical model, confidence, matching manual, matched signals, generations, and machine types.
- `ModelResolution`: resolver result with candidates, machine type candidates, clarification flag, and reason.

All record classes must support `to_dict()` and return JSON-safe structures.

Grounding invariants:

- Authoritative record types must carry a `Citation`.
- `Citation.manual_id` must match the record `manual_id`.
- Page numbers are 1-based.
- Structured table rows must remain `dict[str, str]`; do not flatten row facts into unstructured text.

## 6. M2 Model Resolver Contract

Public API:

```python
resolve_thinkpad_model(query: str, manuals: list[ManualMetadata]) -> ModelResolution
```

Resolver priority:

1. Exact machine type match, for example `21CB`.
2. Exact model plus generation, for example `X1 Carbon Gen 9`.
3. Compact or ordinal generation aliases, for example `T14 Gen2` and `E15 second gen`.
4. Generationless family names return candidates and `clarification_needed=True`.
5. Unsupported models return no candidates and `clarification_needed=True`.

The resolver must be deterministic and must not use live network calls or LLM calls.

## 7. M2 Handoff To M3

Proceed to M3 with these implementation priorities:

- Keep `ManualMetadata` as the manifest-backed source of manual-level truth.
- Use `Citation`, `TableRecord`, `FigureRecord`, `FRUProcedure`, `WarningRecord`, and `DependencyEdge` as parser output targets.
- Replace spike regexes with tested parser modules before relying on them for answers.
- Add synthetic mini HMM fixtures for exact table rows, FRU prerequisites, and citation metadata.
- Keep the local corpus under `data/`; do not commit PDFs or extracted full text.
