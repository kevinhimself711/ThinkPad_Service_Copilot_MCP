# AGENTS.md

This file is the primary instruction file for Codex when developing **ThinkPad_Service_Copilot_MCP**.

The project is a domain-specific extension of `jerry-ai-dev/MODULAR-RAG-MCP-SERVER`:

- Upstream repository: https://github.com/jerry-ai-dev/MODULAR-RAG-MCP-SERVER
- Target project name: `ThinkPad_Service_Copilot_MCP`
- Target role context: internship-oriented project for Agent Development, LLM Application Development, and RAG Engineering.
- Domain: Lenovo ThinkPad Hardware Maintenance Manual, abbreviated as HMM.
- Delivery form: RAG system exposed through MCP tools, then extended into Agentic RAG and a small FRU dependency graph.

Codex must treat this repository as an engineering project, not a toy demo. The final result must be usable for development, evaluation, demonstration, resume bullets, and interview defense.

---

## 1. Core Mission

Build **ThinkPad Service Copilot MCP**, an Agentic RAG MCP Server for ThinkPad Hardware Maintenance Manuals.

The system should convert ThinkPad HMM PDFs into a structured, searchable, citable, and agent-callable knowledge system covering:

- ThinkPad model names, generations, machine types, and manual editions.
- FRU, meaning Field Replaceable Unit, procedures and IDs.
- Error codes and recommended actions.
- Screw specifications, counts, colors, and torque values.
- Removal and replacement procedures.
- Required prerequisite removal chains.
- Diagrams, line drawings, figure captions, and page-level citations.
- DANGER / CAUTION / safety warnings.

The project must prove that the developer can handle real RAG engineering issues:

- Non-trivial PDF ingestion.
- Table extraction and row preservation.
- Figure extraction and image captioning.
- Hybrid retrieval with dense + sparse search.
- Model/generation disambiguation.
- Domain-specific reranking.
- Page-level grounding and citation.
- Golden-set evaluation and regression testing.
- MCP tool design for agent workflows.
- A small, useful Graph RAG component based on FRU dependencies.

---

## 2. Relationship to the Upstream Project

The upstream project is a modular RAG MCP framework. Keep its architecture and improve it through domain-specific extensions instead of rewriting everything.

Preserve these upstream strengths:

- Ingestion pipeline: PDF -> Markdown -> Chunk -> Transform -> Embedding -> Upsert.
- Multi-modal image captioning by converting images to text and attaching captions to chunks.
- Hybrid Search: dense vector retrieval + BM25 sparse retrieval + RRF fusion + optional rerank.
- MCP Server exposing tools to AI clients.
- Streamlit Dashboard for system overview, ingestion tracing, query tracing, and evaluation.
- Ragas + custom evaluation with golden test sets.
- Pluggable providers for LLM, embedding, reranker, vector store, splitter, and evaluator.
- Unit / integration / E2E testing mindset.
- Spec-driven development: update specs before large implementation changes.

Do not turn the project into an unrelated codebase. Most work should be added in domain-specific modules, configuration, tests, and documentation.

Preferred strategy:

1. Start from a working upstream `main` fork if speed matters.
2. Create a branch such as `thinkpad-hmm-domain`.
3. Keep core abstractions stable.
4. Add ThinkPad-specific loaders, metadata enrichers, splitters, rerank rules, MCP tools, evaluation sets, and documentation.
5. Document all deviations from upstream architecture.

---

## 3. Instruction Precedence

When instructions conflict, follow this order:

1. User's direct prompt in the current Codex task.
2. This `AGENTS.md`.
3. `docs/PROJECT_GUIDE.md` or `ThinkPad_Service_Copilot_MCP_PROJECT_GUIDE.md` if present.
4. `DEV_SPEC.md` and any files under `specs/`.
5. Upstream `README.md` and upstream implementation conventions.
6. Existing code style in the nearest module.

If a requirement is ambiguous and implementation can proceed safely, make a conservative engineering decision and record it in the task summary. Ask only when a decision changes architecture, dependencies, data licensing, public API, or evaluation claims.

---

## 4. Required Reading Before Coding

Before making non-trivial changes, inspect the relevant files. Do not rely on memory.

Always check:

- `README.md`
- `DEV_SPEC.md`
- `pyproject.toml`
- `config/` files
- Existing modules under `src/`
- Existing tests under `tests/`
- Project guide files under `docs/`, especially:
  - `docs/PROJECT_GUIDE.md`
  - `docs/DEV_SPEC_THINKPAD.md`
  - `docs/SPIKE_REPORT.md`
  - `docs/EXPERIMENTS.md`
  - `docs/IMPLEMENTATION_LOG.md`
  - `docs/INTERVIEW_NOTES.md` if present locally
  - `docs/EVAL_REPORT.md`

If a referenced file does not exist, do not fail the task. Create it only when it is directly needed by the requested change.

---

## 5. Development Style

### General engineering rules

- Make small, reviewable changes.
- Prefer extension over replacement.
- Preserve upstream interfaces unless there is a documented reason to change them.
- Keep domain-specific logic isolated under clear modules such as `thinkpad`, `domain`, `hmm`, or `service_copilot`.
- Avoid hidden magic. Domain rules must be explicit, testable, and documented.
- Write deterministic code where possible.
- Avoid broad exception swallowing. If recovery is intentional, log the failure and preserve traceability.
- Do not invent unsupported metrics or claim evaluation improvements without recorded experiments.
- Do not hardcode absolute local paths.
- Do not commit secrets, API keys, raw PDFs, extracted full manuals, vector databases, or copyrighted images.

### Code quality

- Use type hints for public functions and domain models.
- Prefer dataclasses or Pydantic models for structured records.
- Keep functions small and focused.
- Use explicit names: `manual_id`, `machine_types`, `fru_id`, `page_start`, `source_url`, `warning_level`.
- Validate all externally loaded YAML/JSON/CSV data.
- Public functions should have concise docstrings explaining domain assumptions.
- Do not introduce a new framework when a small module or function is enough.

### Documentation quality

Every meaningful module should have one of:

- Docstring explaining its role.
- README in the module directory.
- Reference in `docs/DEV_SPEC_THINKPAD.md`.

When adding a feature, update the relevant docs:

- MCP tools -> update `README.md` and tool docs.
- Evaluation changes -> update `docs/EVAL_REPORT.md` or `docs/EXPERIMENTS.md`.
- Ingestion changes -> update `docs/SPIKE_REPORT.md` or `docs/DEV_SPEC_THINKPAD.md`.
- Data schema changes -> update manifest examples and tests.

---

## 6. Domain Non-Negotiables

These rules define the ThinkPad HMM vertical. Do not violate them.

### 6.1 Grounding and citation are mandatory

Any answer generated by the system for a repair, FRU, error code, screw spec, warning, or diagram must include citations containing at minimum:

- `manual_id`
- `source_url` when available
- `page` or page range
- `section` or FRU procedure ID when available

If citation cannot be provided, the tool response must clearly mark the result as unverified and should not present it as authoritative.

### 6.2 Model/generation disambiguation is mandatory

ThinkPad names are ambiguous. Examples:

- `X1 Carbon` may refer to Gen 7, Gen 8, Gen 9, Gen 10, etc.
- `T14` may refer to different generations and AMD/Intel variants.
- One HMM may cover multiple models.

If the user asks for a high-risk procedure without enough model detail, do not guess. Return a clarification requirement such as:

`model generation or machine type is required before returning a unique removal procedure.`

Safe broad search is allowed, but do not produce a final step-by-step repair plan from ambiguous model data.

### 6.3 Tables must be treated as structured data

Error-code tables, FRU tables, and screw-spec tables are core truth sources. Do not rely only on flattened Markdown text if row/column structure matters.

When implementing table extraction:

- Preserve each row as a structured record.
- Keep the page number and manual ID.
- Link rows back to the parent section.
- Store exact strings for codes, FRU IDs, torque values, screw sizes, and counts.
- Add tests for row alignment and exact-match lookup.

### 6.4 Diagrams are retrieval targets, not sources of exact specs

Figure captioning is used to retrieve the right diagram and return it to the technician or agent. Do not infer torque, screw counts, or exact FRU IDs from a figure alone unless the surrounding text or table confirms it.

When implementing image handling:

- Extract embedded images when possible.
- Rasterize page or figure regions as fallback for vector line drawings.
- Store `image_id`, `manual_id`, `page`, `bbox` if available, `caption`, `surrounding_text`, and `related_fru_id` if known.
- Use surrounding page text in the captioning prompt.
- Test at least 10 representative figures during the spike.

### 6.5 FRU procedures must preserve prerequisites

FRU removal procedures often require prior removal of other FRUs. Chunking must not separate the prerequisite chain from the main procedure without a recovery mechanism.

Preferred behavior:

- Split primarily by FRU section such as `1010`, `1020`, `1110` when available.
- Store `fru_id`, `fru_name`, `prerequisites`, `page_start`, `page_end`, and `section_heading`.
- Build a lightweight FRU dependency graph.
- Expose a tool such as `get_fru_dependency_chain`.

### 6.6 Safety warnings must be surfaced

For battery, power, system board, charging, display, or DANGER / CAUTION content:

- Include the original warning context through citation.
- Do not remove safety warnings during chunk refinement.
- If the model/generation is ambiguous, refuse to provide a unique procedure and ask for the exact model/generation/machine type.
- Add `warning_level` metadata where possible.

---

## 7. Data Governance and Copyright Rules

Lenovo HMM PDFs are copyrighted. Public repository content must not redistribute Lenovo manuals or full extracted manual text.

Allowed in the repository:

- Ingestion scripts.
- Manifest templates.
- Source URL lists.
- Small redacted samples.
- Synthetic test fixtures.
- Evaluation schemas.
- Test cases with short excerpts only when legally acceptable.
- Dashboard screenshots that do not reveal full copyrighted pages.
- Instructions for users to download manuals from official Lenovo sources.

Not allowed in the repository:

- Full original HMM PDFs.
- Full extracted Markdown manuals.
- Full vector database snapshots containing manual text.
- Full image dumps of copyrighted diagrams.
- API keys, provider credentials, personal device serial numbers, or private asset information.

Add `.gitignore` coverage for local data directories such as:

- `data/raw/`
- `data/manuals/`
- `data/extracted/`
- `data/vectorstores/`
- `data/images/`
- `chroma/`
- `.env`

If tests need data, create synthetic mini-manual fixtures under `tests/fixtures/`.

---

## 8. Recommended Repository Layout

Preserve upstream layout where possible. Add domain modules with clear boundaries.

Suggested additions:

```text
src/
  thinkpad/
    __init__.py
    manifest.py
    metadata.py
    model_resolver.py
    hmm_loader.py
    hmm_splitter.py
    table_extractor.py
    figure_extractor.py
    image_captioning.py
    fru_graph.py
    domain_reranker.py
    safety.py
    mcp_tools.py
    evals.py

docs/
  PROJECT_GUIDE.md
  DEV_SPEC_THINKPAD.md
  SPIKE_REPORT.md
  EXPERIMENTS.md
  EVAL_REPORT.md
  INTERVIEW_NOTES.md             # local/private; do not commit unless explicitly requested

config/
  thinkpad.yaml
  manuals_manifest.example.yaml

tests/
  thinkpad/
    test_manifest.py
    test_model_resolver.py
    test_hmm_splitter.py
    test_table_extractor.py
    test_fru_graph.py
    test_domain_reranker.py
    test_mcp_tools.py
  fixtures/
    mini_hmm_sample.md
    mini_hmm_tables.json
    mini_manifest.yaml
```

Do not create this layout blindly if the upstream project already has equivalent conventions. Adapt to existing structure.

---

## 9. Domain Data Contracts

Use these contracts as the conceptual target. Exact implementation may use dataclasses, Pydantic, TypedDict, or project-native models.

### 9.1 Manual metadata

```python
class ManualMetadata:
    manual_id: str
    title: str
    family: str | None
    models: list[str]
    generations: list[str]
    machine_types: list[str]
    year: int | None
    edition: str | None
    source_type: str
    source_url: str
    document_type: str = "hmm"
    local_path: str | None = None
```

### 9.2 Chunk metadata

```python
class ThinkPadChunkMetadata:
    chunk_id: str
    manual_id: str
    models: list[str]
    generations: list[str]
    machine_types: list[str]
    section: str | None
    section_type: str | None
    fru_id: str | None
    fru_name: str | None
    error_codes: list[str]
    screw_specs: list[str]
    warning_level: str | None
    page_start: int | None
    page_end: int | None
    source_url: str | None
    has_image: bool
    image_ids: list[str]
```

### 9.3 Table record

```python
class TableRecord:
    record_id: str
    manual_id: str
    page: int
    table_type: str  # error_code | fru | screw_spec | diagnostic | unknown
    columns: list[str]
    row: dict[str, str]
    parent_section: str | None
    source_url: str | None
```

### 9.4 Figure record

```python
class FigureRecord:
    image_id: str
    manual_id: str
    page: int
    bbox: tuple[float, float, float, float] | None
    caption: str
    surrounding_text: str
    related_fru_id: str | None
    related_component: str | None
    storage_uri: str
    source_url: str | None
```

### 9.5 FRU dependency node

```python
class FRUNode:
    model: str
    manual_id: str
    fru_id: str
    fru_name: str
    prerequisites: list[str]
    page_start: int | None
    page_end: int | None
    warnings: list[str]
    related_image_ids: list[str]
```

---

## 10. MCP Tool Design

The upstream general tool `query_knowledge_hub` may remain available, but ThinkPad-specific tools must be added because this project is agent-oriented.

Preferred MCP tools:

### `list_supported_models`

Returns known model names, generations, machine types, and manual IDs.

### `resolve_thinkpad_model`

Input: free-form model text such as `T14 Gen2`, `X1 Carbon 20XW`, or `E15 second gen`.

Output:

- canonical model name
- generation
- machine type candidates
- matching manuals
- confidence
- clarification needed flag

### `query_thinkpad_service`

General grounded search over HMM content. Use for broad questions and fallback retrieval.

### `get_fru_procedure`

Returns the removal/replacement procedure for a component or FRU under a specific model.

Must include:

- procedure steps
- prerequisites
- warnings
- citations
- related diagrams

### `get_fru_dependency_chain`

Traverses the FRU dependency graph and returns the ordered prerequisite chain.

This is the core Graph RAG tool.

### `lookup_error_code`

Exact lookup for numeric error codes and diagnostic actions.

Must prefer structured table records over free-text chunks.

### `get_screw_spec`

Exact lookup for screw size, count, color, and torque if available.

Must prefer structured table records.

### `get_related_diagram`

Returns diagram records and image references for a component/FRU under a model.

Must not claim image-derived torque/specs unless verified by text/table.

### `get_safety_warnings`

Returns relevant DANGER / CAUTION / battery / ESD / system-board warnings for a model/component.

### `compare_generations`

Compares the same component/procedure across model generations, used for disambiguation demos and evaluation.

---

## 11. Retrieval and Reranking Rules

Keep upstream hybrid retrieval. Add domain-specific rules after coarse retrieval.

### Dense retrieval should help with semantic queries

Examples:

- `laptop will not power on`
- `after replacing motherboard it does not charge`
- `how to remove the part under the keyboard`

### Sparse BM25 should help with exact queries

Examples:

- `0271`
- `M2.5 x 5 mm`
- `0.294 Nm`
- `20XW`
- `FRU 1020`

### Domain reranker priority

Rerank candidates using explicit, explainable rules:

1. Exact machine type match.
2. Exact model + generation match.
3. Exact manual ID match if user or resolver supplied it.
4. Exact FRU ID, error code, torque value, or screw spec match.
5. Section type match: procedure > table row > general description, depending on tool.
6. Warning/safety section boost for safety-specific tools.
7. Prefer official Lenovo source over mirrors when duplicate content exists.
8. Prefer newer edition only when model/generation is identical.
9. Never allow a different generation to outrank the specified generation just because semantic similarity is higher.

Every domain rerank decision should be traceable in query logs or debug output.

---

## 12. Ingestion Spike First

Before full-scale ingestion, implement a risk-validation spike using 5-8 representative manuals.

The spike must validate four risks:

### R1: Table extraction

Validate error-code tables, FRU tables, and screw-spec tables. Confirm row/column alignment.

### R2: Figure extraction and caption usefulness

Validate embedded image extraction and rasterization fallback for vector line drawings. Caption at least 10 figures and inspect quality.

### R3: Version/model metadata

Validate extracting `models`, `generation`, `machine_types`, `edition`, `year`, and `source_url` from title page, filename, and manifest.

### R4: FRU procedure chunking and prerequisite preservation

Validate that FRU sections and their prerequisite chains are preserved.

Suggested MVP manuals should cover:

- T14 Gen 2
- T14 Gen 3
- X1 Carbon Gen 9
- X1 Carbon Gen 10
- E15 Gen 2
- P1 Gen 4 or X1 Extreme Gen 4
- At least one manual covering multiple models

After spike, write or update `docs/SPIKE_REPORT.md` with:

- Manuals tested.
- Extraction success/failure samples.
- Table extraction findings.
- Figure extraction findings.
- Metadata extraction findings.
- Chunking findings.
- Decisions for full ingestion.

Do not ingest 50 manuals until the spike has been documented.

---

## 13. Evaluation Requirements

Evaluation is not optional. This project must avoid subjective claims such as "it works well".

### Golden test set categories

Create at least 30 tests for MVP and 80-100 tests for full version.

Categories:

1. Exact lookup:
   - Error codes.
   - FRU IDs.
   - Screw specs.
   - Torque values.

2. Procedure lookup:
   - Component removal steps.
   - Replacement notes.
   - Required pre-removal steps.

3. Model/generation ambiguity:
   - `X1 Carbon battery removal` without generation should request clarification or return candidates.
   - `X1 Carbon Gen 9 battery removal` should select the correct manual.

4. Multi-modal retrieval:
   - Queries asking for diagrams or figures.
   - Verify that correct figure references are returned.

5. Safety grounding:
   - Battery, system board, ESD, DANGER/CAUTION warnings.

6. Negative tests:
   - Unsupported models.
   - Ambiguous model names.
   - Missing generation for high-risk procedure.
   - Non-ThinkPad or non-HMM questions.

### Baselines to compare

Where feasible, evaluate:

- Dense only.
- BM25 only.
- Hybrid without rerank.
- Hybrid + generic rerank.
- Hybrid + ThinkPad domain rerank.
- Hybrid + domain rerank + FRU graph for dependency questions.

### Metrics

Track at minimum:

- Hit@K.
- MRR.
- Context precision.
- Model/generation accuracy.
- Citation accuracy.
- Answer faithfulness.
- Safety-warning recall for safety queries.
- Tool-call success rate for agent workflows.
- End-to-end latency.

Record experiments in `docs/EXPERIMENTS.md` or `docs/EVAL_REPORT.md`.

---

## 14. Agentic RAG and Graph RAG Scope

After the MCP server works, deepen the project in this order:

1. Build FRU dependency graph.
2. Expose graph traversal through `get_fru_dependency_chain`.
3. Build a simple repair-planning agent client.
4. Keep backend productionization to table-stakes unless explicitly requested.

### Agent workflow

The agent should handle a realistic maintenance task:

1. Parse user symptom or repair goal.
2. Resolve model/generation.
3. Ask for clarification when model is ambiguous.
4. Query error code or symptom table if relevant.
5. Identify candidate FRU/procedure.
6. Retrieve procedure from MCP.
7. Traverse FRU dependency graph.
8. Retrieve related diagram and safety warnings.
9. Produce an ordered repair plan with citations.

Do not build a complex multi-agent framework unless requested. A single well-instrumented tool-calling or ReAct-style agent is enough.

### Graph RAG scope

Keep Graph RAG small and useful.

Focus entities:

- Model.
- Manual.
- FRU.
- Procedure.
- Error code.
- Diagram.
- Screw spec.
- Warning.

Focus relationships:

- `MODEL_HAS_MANUAL`
- `MANUAL_COVERS_MODEL`
- `MODEL_HAS_FRU`
- `FRU_REQUIRES_PREREQUISITE_FRU`
- `ERROR_CODE_SUGGESTS_FRU_OR_ACTION`
- `FRU_HAS_PROCEDURE`
- `FRU_HAS_DIAGRAM`
- `FRU_HAS_SCREW_SPEC`
- `PROCEDURE_HAS_WARNING`

Do not use Graph RAG as a buzzword. Use it only for relationship and multi-hop questions that vector retrieval handles poorly.

---

## 15. Productionization Scope

For internship-oriented Agent/LLM/RAG roles, productionization should be useful but not dominate the project.

Required minimum:

- Dockerfile.
- `docker-compose.yml` for MCP server, dashboard, vector store paths, and local data volumes.
- HTTP or Streamable HTTP MCP mode if upstream supports it or it is reasonable to add.
- Health check endpoint or command.
- Structured logging for ingestion and query pipeline.
- Basic GitHub Actions running tests and lint checks.

Optional only if explicitly requested:

- Kubernetes manifests.
- Prometheus/Grafana.
- Multi-tenant auth.
- Full role-based access control.

Do not delay RAG, evaluation, or agent workflow work to overbuild infrastructure.

---

## 16. Testing Instructions

Before finishing a coding task, run the most relevant tests.

Use existing project commands if available. Discover them from `pyproject.toml`, `Makefile`, or CI config.

Common commands may include:

```bash
pytest
pytest tests/thinkpad
ruff check .
python -m pytest tests/thinkpad/test_hmm_splitter.py
```

Do not claim tests passed unless they were actually run. If tests cannot be run because dependencies, data, or credentials are missing, state exactly what was not run and why.

### Live provider validation

Live paid provider tests are allowed when they materially reduce implementation risk or validate behavior that mocks cannot cover.

Rules:

- Use credentials only through environment variables such as `DASHSCOPE_API_KEY`.
- Do not write API keys to `config/`, `.env`, docs, tests, command output files, commits, or logs.
- Prefer the smallest useful live test first, then scale only when needed.
- Record live commands, aggregate results, failures, and follow-up decisions in `docs/EXPERIMENTS.md` and `docs/IMPLEMENTATION_LOG.md`.
- Keep generated indexes, traces, and provider outputs under ignored local data paths.

### Test expectations

Add tests for every new domain behavior:

- Manifest parsing.
- Model resolver ambiguity handling.
- Table row preservation.
- FRU section splitting.
- Prerequisite extraction.
- Domain rerank scoring.
- Citation formatting.
- Safety refusal or clarification logic.
- MCP tool input/output schema.

Use synthetic fixtures rather than copyrighted full manuals.

---

## 17. Error Handling and Observability

The project must be inspectable. When something fails, developers should know where and why.

For ingestion:

- Record per-manual status.
- Record table extraction count.
- Record figure extraction count.
- Record rasterization fallback count.
- Record metadata extraction confidence.
- Record chunk count by section type.

For queries:

- Log normalized query.
- Log resolved model candidates.
- Log dense hits.
- Log sparse hits.
- Log RRF-fused hits.
- Log rerank score and domain-rule adjustments.
- Log final citations.
- Log latency per stage.

Use existing dashboard/trace infrastructure when possible.

---

## 18. LLM Usage Rules

LLM calls may be used for:

- Image captioning.
- Chunk refinement.
- Metadata extraction with validation.
- Answer generation from retrieved context.
- Agent planning.

LLM calls must not be used as the sole source of truth for:

- Error codes.
- Torque values.
- Screw sizes and counts.
- FRU IDs.
- Model/generation identity.
- Safety warnings.

For exact facts, prefer structured table records and cited HMM text.

When LLM output is parsed into structured data:

- Validate against schema.
- Preserve source snippets and page references.
- Add tests for malformed outputs.
- Prefer deterministic regex/rules when HMM structure is regular.

---

## 19. Task Workflow for Codex

For each task, follow this workflow:

1. Restate the goal internally from the user request.
2. Inspect relevant files.
3. Identify the smallest safe change.
4. Update specs/docs first if the change affects architecture or public APIs.
5. Implement code.
6. Add or update tests.
7. Run relevant tests.
8. Update documentation.
9. For any repo-state implementation, update `docs/IMPLEMENTATION_LOG.md` with detailed file-level facts.
10. For any non-trivial milestone or feature implementation, update the local private `docs/INTERVIEW_NOTES.md` with interview questions grounded in the real work when that file is present.
11. Summarize changes, tests run, and remaining risks.

Do not create large unrelated rewrites. Do not rename existing modules or reformat the entire repository unless the task explicitly asks.

Implementation documentation is more detailed than the final Codex response. The final response can stay concise, but the permanent docs must preserve enough detail for later review, interview preparation, and handoff.

---

## 20. Definition of Done

A feature is done only when these are true:

- Code compiles/imports.
- Relevant tests pass or a clear reason is documented.
- Public behavior is documented.
- Domain invariants are preserved.
- Citations are present for grounded answers.
- No copyrighted manuals or generated vector stores are committed.
- The change is traceable to a project phase, spec item, or user request.
- Non-trivial implementation facts are recorded in `docs/IMPLEMENTATION_LOG.md`.
- Interview-relevant decisions, tradeoffs, and questions are recorded in local private `docs/INTERVIEW_NOTES.md` when that file is present.

For retrieval/evaluation features, also require:

- At least one golden test or synthetic fixture.
- Baseline or before/after comparison when feasible.
- A short note in `docs/EXPERIMENTS.md` or `docs/EVAL_REPORT.md`.

---

## 21. Phase Roadmap

Use this roadmap unless the user gives a different one.

### M0: Repository adaptation

- Fork/clone upstream.
- Create branch `thinkpad-hmm-domain`.
- Add this `AGENTS.md`.
- Add `docs/PROJECT_GUIDE.md` if not present.
- Confirm setup and baseline tests.

### M1: Spike

- Add manifest template.
- Test 5-8 representative HMM manuals locally.
- Validate R1-R4.
- Write `docs/SPIKE_REPORT.md`.

### M2: Domain data model

- Implement metadata models.
- Implement manifest parser.
- Implement model resolver.
- Add synthetic fixture tests.

### M3: Ingestion enhancements

- Add HMM-aware splitter.
- Add table extraction pipeline.
- Add figure extraction fallback.
- Add image-caption integration.
- Preserve citations and page numbers.

### M4: Retrieval and rerank

- Add domain filters.
- Add domain reranker.
- Add sparse exact-match improvements.
- Add trace outputs.

### M5: MCP tools

- Implement ThinkPad-specific MCP tools.
- Preserve upstream generic tools if useful.
- Add schema tests and sample tool calls.

### M6: Evaluation and dashboard

- Create golden test set.
- Compare retrieval baselines.
- Add dashboard views or traces for ThinkPad-specific stages.

### M7: Graph RAG

- Extract FRU dependency graph.
- Add graph traversal tool.
- Evaluate dependency-chain questions.

### M8: Agent client

- Implement simple tool-calling repair planning agent.
- Add trajectory examples.
- Evaluate tool-call success and plan correctness.

### M9: Packaging and interview readiness

- Add Docker and CI.
- Write final README.
- Write demo script.
- Write resume bullets and interview notes.

---

## 22. Commit and PR Guidance

If committing is requested:

- Use clear commit messages.
- Prefer one conceptual change per commit.
- Mention docs/tests in the commit body when relevant.

Suggested commit style:

```text
feat(thinkpad): add FRU-aware splitter and metadata schema
fix(thinkpad): preserve error-code table row alignment
test(thinkpad): add model resolver ambiguity fixtures
docs: add ingestion spike report
```

Never commit local data artifacts, raw manuals, `.env`, vector stores, or large generated image dumps.

---

## 23. Demo and Resume Orientation

Implementation choices should support a strong demo.

Primary demo query examples:

- `X1 Carbon Gen 9 battery removal procedure`
- `T14 Gen 2 system board full prerequisite chain`
- `E15 Gen 2 error code 0271`
- `Find the fan assembly removal diagram for P1 Gen 4`
- `X1 Carbon battery removal` should trigger disambiguation if generation is missing.

The final project should support this resume-level claim:

`Built a domain-specific Agentic RAG MCP Server for ThinkPad Hardware Maintenance Manuals, enabling AI agents to retrieve model-specific FRU procedures, error codes, safety warnings, screw specifications, and repair diagrams with page-level citations. Extended the base modular RAG MCP framework with HMM-aware ingestion, hybrid retrieval, ThinkPad-specific reranking, FRU dependency graph traversal, MCP tools, and golden-set evaluation.`

Do not implement features that cannot be explained in this narrative.

---

## 24. What Not To Do

Do not:

- Build a generic PDF chatbot and call it done.
- Skip the ingestion spike.
- Ingest 50 manuals before validating table/figure/chunking risks.
- Commit copyrighted Lenovo manuals or extracted full text.
- Guess model generation for high-risk repair procedures.
- Present uncited LLM output as official repair guidance.
- Overbuild K8s/monitoring before RAG and evaluation are solid.
- Replace upstream architecture without a strong reason.
- Add dependencies without checking existing equivalents.
- Hide failing tests or claim unrun tests passed.
- Inflate metrics without reproducible evaluation artifacts.

---

## 25. Final Operating Principle

This project succeeds when it demonstrates engineering judgment.

The goal is not to maximize feature count. The goal is to show that the developer can take a modular RAG MCP framework and turn it into a realistic vertical Agentic RAG system by solving the domain's actual failure modes:

- ambiguous model names,
- exact FRU/error/screw facts,
- PDF tables,
- vector line drawings,
- prerequisite chains,
- safety warnings,
- citations,
- evaluations,
- and agent-callable tool design.

When unsure, choose the path that makes the system more grounded, more testable, more inspectable, and easier to explain in an internship interview.
