# ThinkPad Service Copilot MCP - Project Guide v2.1

> Canonical guide: `docs/PROJECT_GUIDE.md`
> Consolidated: 2026-06-09
> Project: `ThinkPad_Service_Copilot_MCP`
> Upstream: `jerry-ai-dev/MODULAR-RAG-MCP-SERVER`
> Upstream URL: https://github.com/jerry-ai-dev/MODULAR-RAG-MCP-SERVER
> Current domain branch: `thinkpad-hmm-domain`
> Domain: Lenovo ThinkPad Hardware Maintenance Manuals, abbreviated HMM

This file is the canonical project guide after the v2.1 consolidation. Git history is enough for older drafts.

`AGENTS.md` still has higher instruction precedence. This guide defines project direction, milestone scope, data contracts, and engineering boundaries.

---

## 1. Project Positioning

ThinkPad Service Copilot MCP is a domain-specific RAG system for Lenovo ThinkPad Hardware Maintenance Manuals. It exposes grounded service-manual knowledge through MCP tools in later phases and can be extended into a small Agentic RAG workflow with a FRU dependency graph.

The project is primarily a RAG engineering project:

```text
Core capability: RAG
Delivery interface: MCP
Deepening direction: Agentic RAG + small FRU dependency graph
```

The goal is not a generic PDF chatbot. The project must demonstrate practical engineering judgment on real HMM failure modes:

- model and generation ambiguity
- machine type disambiguation
- exact FRU, error-code, screw, and torque facts
- PDF table row preservation
- diagram and vector-line extraction
- prerequisite FRU chains
- safety warnings
- citations
- evaluation and regression tests
- agent-callable tool boundaries

The final interview-level claim should be:

```text
Built a domain-specific Agentic RAG MCP Server for ThinkPad Hardware Maintenance Manuals,
enabling AI agents to retrieve model-specific FRU procedures, error codes, safety warnings,
screw specifications, and repair diagrams with page-level citations.
```

---

## 2. Relationship To Upstream

The upstream repository is a modular RAG MCP framework. This project extends it instead of replacing it.

Preserve upstream strengths:

- PDF ingestion flow
- Markdown/text extraction
- chunking and transform pipeline
- embedding and vector-store abstraction
- hybrid retrieval with dense + BM25 + RRF
- optional reranking
- MCP server surface
- dashboard and tracing mindset
- Ragas/custom evaluation mindset
- provider-pluggable architecture

Add ThinkPad-specific work around the upstream core:

- `src/thinkpad/` domain schemas, manifest validation, resolver, splitters, extractors, rerankers, and MCP adapters
- `config/manuals_manifest.example.yaml` committed manifest template
- `data/manifests/manuals_manifest.yaml` local real manifest, ignored
- `data/manuals/` local PDFs, ignored
- `data/extracted/` local spike outputs and future parsed artifacts, ignored
- `tests/thinkpad/` synthetic domain tests
- `docs/DEV_SPEC_THINKPAD.md`, `docs/SPIKE_REPORT.md`, `docs/EXPERIMENTS.md`, `docs/EVAL_REPORT.md`

Do not rewrite the generic MCP server, vector store layer, dashboard, provider abstractions, or evaluation framework unless an upstream limitation is documented.

---

## 3. Current Repository Reality

The repository has completed M0-M8.1 and is ready for M9 packaging/interview-readiness work. M8.1 remediated the M8 live LLM golden-set failures, while provider fallback, high p95 latency, and stress-case alias gaps remain tracked risks.

Current milestone status:

| Milestone | Status | Notes |
|---|---|---|
| M0 | Complete | Upstream baseline and branch bootstrap are recorded. |
| M1 | Complete with risk | 8 official Lenovo HMMs were downloaded and scanned locally; extraction quality was not fully human-audited. |
| M2 | Complete | Domain dataclasses, manifest validation, and model resolver are implemented. |
| M3 | Complete with risk | Local HMM-aware extraction produces structured candidates, not gold facts. |
| M4 | Complete with risk | DashScope providers, retrieval corpus, index CLI, and retrieval facade exist; broader retrieval eval remains future work. |
| M5 | Complete | ThinkPad-specific MCP evidence tools are registered and tested. |
| M6 | Complete | Golden evaluation baseline and lightweight dashboard view are implemented. |
| M6.1 | Complete | Screw-spec normalization regression was fixed and re-evaluated. |
| M7 | Complete with risk | FRU dependency graph traversal is exposed as MCP evidence; graph edges still inherit M3 extraction-candidate risk. |
| M7.1 | Complete | M0-M7 completion audit and live regression are recorded. |
| M8 | Complete with risk | Local repair-planning agent, 96-case benchmark, live retrieval baseline, live LLM baseline, and stress benchmark are implemented; the initial live LLM baseline had 5 recorded failures. |
| M8.1 | Complete with risk | LLM composition hardening, deterministic evidence-only repair fallback, provider-failure classification, and stress candidate cleanup are implemented; 96-case live LLM now passes, while generated stress cases still show component alias gaps. |

Canonical audit report: `docs/M0_M7_PROGRESS_AUDIT.md`.
Canonical M8 performance report: `docs/M8_AGENT_PERFORMANCE_BASELINE.md`.
Canonical M8.1 remediation report: `docs/M8_1_REMEDIATION_REPORT.md`.

Canonical paths:

```text
config/manuals_manifest.example.yaml      committed example manifest
data/manifests/manuals_manifest.yaml      real local manifest, ignored
data/manuals/                             real local PDFs, ignored
data/extracted/                           local spike and parsed outputs, ignored
src/thinkpad/                             ThinkPad domain modules
tests/thinkpad/                           domain tests using synthetic fixtures
```

ThinkPad local-data and milestone scripts currently present:

```text
scripts/thinkpad_discover_manuals.py
scripts/thinkpad_download_manuals.py
scripts/thinkpad_spike_inspect.py
scripts/thinkpad_extract_hmm.py
scripts/thinkpad_build_retrieval_index.py
scripts/thinkpad_query_retrieval.py
scripts/thinkpad_evaluate.py
scripts/thinkpad_audit_milestones.py
scripts/thinkpad_agent_plan.py
scripts/thinkpad_agent_evaluate.py
scripts/thinkpad_generate_agent_eval_candidates.py
```

Current MCP tools expose structured evidence. M8 adds a local Python/CLI repair-planning agent client but does not yet expose a `plan_repair` MCP tool.

---

## 4. M1 Actual Results

M1 used 8 official Lenovo ThinkPad HMM PDFs as the MVP risk-validation set:

1. ThinkPad T14 Gen 2 / P14s Gen 2 HMM
2. ThinkPad T14 Gen 3 / P14s Gen 3 HMM
3. ThinkPad T480 HMM
4. ThinkPad T490 HMM
5. ThinkPad X1 Carbon Gen 9 / X1 Yoga Gen 6 HMM
6. ThinkPad X1 Carbon Gen 10 / X1 Yoga Gen 7 HMM
7. ThinkPad E14 Gen 2 / E15 Gen 2 HMM
8. ThinkPad P1 Gen 4 / X1 Extreme Gen 4 HMM

Official discovery path that worked:

```text
Lenovo self-repair product page
-> extract Guid and ParentGuids
-> call Lenovo api/v4/contents/recommendmanual
-> select hardwareMaintenanceManual.pdfs
```

Download lesson:

- Large Lenovo PDFs can appear to finish early as partial downloads.
- The downloader must compare remote `Content-Length`.
- The downloader must support HTTP Range resume.
- The downloader must write SHA256 and local file size back into the local manifest.

Full scan results:

| Metric | Count |
|---|---:|
| Manuals | 8 |
| Total pages | 877 |
| Total PDF bytes | 416,466,848 |
| Table candidates | 768 |
| PyMuPDF structured table candidates | 331 |
| Figure candidates | 773 |
| Raster fallback pages | 591 |
| FRU section candidates | 555 |
| Safety markers | 687 |

M1 conclusion:

- The corpus is viable.
- Upstream PDF discovery/ingestion can remain the base.
- Table extraction, figure extraction, FRU sectioning, and metadata disambiguation are real risks.
- Automated full scan is complete, but manual row/column, diagram, and FRU-chain quality review is still a prerequisite for M3. Do not pretend M1 proved extraction quality.

---

## 5. Data Governance

Lenovo HMM PDFs are copyrighted. The repository must not redistribute manuals or full extracted manual text.

Allowed in Git:

- official Lenovo source URLs
- manifest examples and schema validators
- discovery, download, and inspection scripts
- aggregate metrics and engineering decisions
- synthetic fixtures
- short redacted examples when legally acceptable
- evaluation schemas and test cases

Not allowed in Git:

- full Lenovo HMM PDFs
- full extracted Markdown/text
- full image or page-render dumps
- vector-store snapshots containing manual text
- API keys, credentials, serial numbers, or private device data

Ignored local data paths:

```text
data/raw/
data/manuals/
data/manifests/
data/extracted/
data/vectorstores/
data/images/
storage/
chroma/
.env
```

---

## 6. Documentation Assets

This project keeps implementation memory as a first-class artifact. Codex final replies can be short, but permanent project documents must preserve enough detail for later review, interview preparation, and handoff.

Canonical documentation roles:

| Document | Purpose |
|---|---|
| `docs/PROJECT_GUIDE.md` | Project direction, milestone boundaries, domain rules, and roadmap |
| `docs/DEV_SPEC_THINKPAD.md` | Current engineering contracts for ThinkPad domain modules |
| `docs/EXPERIMENTS.md` | Experiment hypotheses, commands, results, and technical decisions |
| `docs/IMPLEMENTATION_LOG.md` | File-level implementation facts, tests, risks, and handoff notes per milestone |
| `docs/INTERVIEW_NOTES.md` | Local private interview questions and answer anchors grounded in real implementation evidence; intentionally not committed |
| `docs/SPIKE_REPORT.md` | M1 risk-validation findings |
| `docs/EVAL_REPORT.md` | Retrieval/answer evaluation once available |

Implementation documentation rules:

- Every milestone implementation must update `docs/IMPLEMENTATION_LOG.md`.
- Every non-trivial milestone or feature should add interview questions to local private `docs/INTERVIEW_NOTES.md` when that file is present.
- Interview notes must separate upstream framework capabilities from ThinkPad-specific work.
- Missing test results, manual checks, or future plans must be marked honestly; do not convert plans into claims.

---

## 7. HMM Data Unit Taxonomy

HMMs must not be treated as one flat stream of chunks. They contain different data units with different extraction and retrieval rules.

| Unit | Examples | Storage Target | Retrieval Priority | Citation Required |
|---|---|---|---|---|
| Manual metadata | title, edition, models, machine types | `ManualMetadata` | filters/resolver | yes |
| Service policy | trained technician, FRU policy | chunk | dense + BM25 | yes |
| Error table | POST codes, beep errors, symptom rows | `TableRecord` | exact/BM25 first | yes |
| FRU table | FRU names, CRU flags, part classes | `TableRecord` | exact/BM25 first | yes |
| Screw spec | size, count, color, torque | `TableRecord` | exact lookup first | yes |
| FRU procedure | removal/replacement steps | `FRUProcedure` | section + metadata | yes |
| Prerequisite chain | remove 1010 before 1050 | `DependencyEdge` | graph traversal | yes |
| Diagram/figure | line drawing, exploded view | `FigureRecord` | diagram search | yes |
| Safety warning | DANGER, CAUTION, battery, ESD | `WarningRecord` | safety boost | yes |

Tables must preserve rows and columns. Figures are retrieval targets, not sources of exact torque/spec facts unless confirmed by text or table records.

---

## 8. Answer Policy

Authoritative service answers must include citations with at least:

- `manual_id`
- `source_url`
- `page_start` and optional `page_end`
- section or FRU ID when available

If the system cannot cite a source, it must mark the result as unverified and avoid presenting it as official guidance.

Model/generation disambiguation is mandatory for high-risk service procedures. For example:

```text
X1 Carbon battery removal
```

must not produce a unique repair plan unless generation or machine type is resolved. The correct behavior is to ask for generation or machine type, or return candidates.

LLMs may help with:

- image captioning
- metadata extraction with validation
- answer synthesis from retrieved context
- agent planning

LLMs must not be the sole source of truth for:

- error codes
- torque values
- screw sizes and counts
- FRU IDs
- model/generation identity
- safety warnings

---

## 9. Safety Boundary

The project can retrieve and cite HMM content. It must not:

- bypass passwords or security mechanisms
- generate instructions for unauthorized access
- replace official Lenovo service qualifications
- omit DANGER/CAUTION context for battery, power, system board, display, ESD, or charging topics
- guess a unique procedure when model/generation is ambiguous

Safety warnings should be returned as cited context, not buried inside generic generated prose.

---

## 10. M2 Scope

M2 is the domain data-model milestone.

M2 implements internal Python domain APIs only:

```python
load_manifest(path) -> list[ManualMetadata]
resolve_thinkpad_model(query: str, manuals: list[ManualMetadata]) -> ModelResolution
Citation(...)
TableRecord(...)
FigureRecord(...)
FRUProcedure(...)
WarningRecord(...)
DependencyEdge(...)
```

M2 does not implement:

- new MCP tools
- retrieval or reranking
- full ingestion
- vector-store upsert
- image captioning
- FRU graph traversal
- generated repair answers
- new PDF downloads
- new full scans

M2 implementation priorities:

1. Define dataclass domain records in `src/thinkpad/models.py`.
2. Extend `src/thinkpad/manifest.py` with M1/M2 metadata fields and status-aware validation.
3. Add `src/thinkpad/model_resolver.py`.
4. Add synthetic tests for manifest validation, citation contracts, and resolver ambiguity.
5. Update `docs/DEV_SPEC_THINKPAD.md` and `docs/EXPERIMENTS.md`.

---

## 11. M2 Data Contracts

`ManualMetadata` required core:

```python
manual_id: str
title: str
models: list[str]
generations: list[str]
machine_types: list[str]
source_type: str = "lenovo_official"
source_url: str
product_page_url: str | None
local_pdf_path: str
document_type: str = "hmm"
language: str = "en"
```

`ManualMetadata` M1/M2 extension:

```python
year: int | None
edition: str | None
page_count: int | None
checksum_sha256: str | None
file_size_bytes: int | None
product_guids: list[str]
spike_status: "planned" | "discovered" | "downloaded" | "validated"
notes: list[str]
```

Status validation:

- `planned` and `discovered` may lack checksum and file size.
- `downloaded` and `validated` require checksum, file size, and local path.
- `validated` also requires page count.
- URL validation is content-based and does not make live network calls.

Core record contracts:

- `Citation`: mandatory page-level grounding.
- `TableRecord`: one preserved row with columns, row dict, page, table type, and citation.
- `FigureRecord`: diagram/page-render reference with caption or surrounding text and citation.
- `FRUProcedure`: procedure ID, FRU ID/name, prerequisites, steps, warnings, images, citation.
- `WarningRecord`: safety marker with warning level, text, page, and citation.
- `DependencyEdge`: directed prerequisite relation between FRUs.
- `ModelResolution`: conservative resolver output with candidates, confidence, machine types, and `clarification_needed`.

---

## 12. Model Resolver Policy

Resolver priority:

1. Exact machine type match, such as `21CB` or `20XW`.
2. Exact model + generation match, such as `X1 Carbon Gen 9`.
3. Alias match, such as `T14 Gen2` or `E15 second gen`.
4. Generationless family match returns candidates and `clarification_needed=True`.
5. Unsupported model returns no candidates and `clarification_needed=True`.

The resolver must not guess across generations. A semantically similar manual from another generation must not outrank the specified generation just because the text is similar.

---

## 13. Retrieval And Reranking Direction

Retrieval is not part of M2, but later stages should preserve these rules.

Dense retrieval should help with semantic queries:

- `laptop will not power on`
- `after replacing motherboard it does not charge`
- `how to remove the part under the keyboard`

Sparse/BM25 and exact lookup should help with:

- `0271`
- `M2.5 x 5 mm`
- `0.294 Nm`
- `20XW`
- `FRU 1020`

Domain reranking should prefer:

1. exact machine type
2. exact model and generation
3. exact manual ID if supplied
4. exact FRU ID, error code, screw spec, or torque
5. section type required by the tool
6. safety section for safety tools
7. official Lenovo source over mirrors
8. newer edition only when model/generation is identical

---

## 14. Milestone Roadmap

| Milestone | Scope | Definition of Done |
|---|---|---|
| M0 | Repository adaptation | upstream baseline preserved, branch created, docs/gitignore added |
| M1 | 8-manual risk spike | official discovery/download/full scan complete, aggregate report written, no PDF committed |
| M2 | Domain data model | schemas, manifest validator, model resolver, synthetic tests, docs updated |
| M3 | Ingestion enhancements | HMM-aware splitter, table extraction, figure fallback, citation preservation |
| M4 | Retrieval and rerank | domain filters, exact sparse improvements, traceable rerank rules |
| M5 | MCP tools | ThinkPad-specific tool schemas and sample calls |
| M6 | Evaluation/dashboard | golden set, baseline comparisons, trace/dashboard views |
| M7 | Graph RAG | FRU dependency graph and traversal tool |
| M8 | Agent client | local tool-calling repair-planning workflow plus trajectory/faithfulness baseline |
| M9 | Packaging/interview readiness | Docker/CI, final README, demo script, resume and interview notes |

Every milestone DoD also includes:

- update `docs/IMPLEMENTATION_LOG.md` with concrete file-level facts, commands, validation results, risks, and handoff notes
- update local private `docs/INTERVIEW_NOTES.md` with 3-8 grounded interview questions when present and when the milestone or feature is non-trivial

M1 actual status:

- Automated official discovery, download, integrity verification, upstream dry run, and full structural scan are complete.
- Manual quality review for table rows, figure usefulness, and FRU chain correctness remains before M3 production ingestion.

---

## 15. M2 Verification Commands

Expected local commands:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
.\.venv\Scripts\python -m pytest tests\unit\test_smoke_imports.py -q
.\.venv\Scripts\ruff check src\thinkpad tests\thinkpad scripts\thinkpad_*.py
```

Do not claim a test passed unless it was run.

---

## 16. Open Risks

Current risks carried forward after M8.1:

- M1/M3 extraction artifacts are structured candidates, not fully human-audited gold facts.
- Figure and diagram records are useful retrieval targets, but exact specs must still come from text/table evidence.
- Some M3-derived stress cases still expose component alias and procedure-applicability gaps.
- M4/M6/M7/M8 golden metrics are scoped to committed fixtures and do not represent every possible technician query.
- M8.1 live LLM generation passes the 96-case committed fixture, but the run still recorded provider fallback/recovery and high `latency_ms_p95`.
- The local manifest and local index contain real operational metadata/artifacts, but committed examples must remain safe and copyright-light.

Engineering response:

- keep deterministic evidence tools as the source of truth
- preserve citations everywhere
- prefer structured table records for exact facts
- use live provider tests when they reduce risk, but record provider fallback and failure rates honestly
- keep LLM composition validation in place before exposing final repair planning through MCP

---

## 17. Final Operating Principle

The project succeeds when it is grounded, testable, inspectable, and explainable.

Do not maximize feature count. Solve the domain's real failure modes in order:

```text
model ambiguity
exact facts
tables
figures
FRU prerequisites
safety warnings
citations
evaluation
MCP tool design
agent workflow
```
