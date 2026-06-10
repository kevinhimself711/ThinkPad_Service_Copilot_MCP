# Evaluation Report

> Current scope: M4 retrieval baseline. This file records reproducible evaluation status and gaps. It does not claim final answer quality.

## M4 Retrieval Baseline

- Date: 2026-06-10
- Milestone: M4 ThinkPad Retrieval + DashScope Provider Wiring
- Corpus input: local ignored M3 extraction artifacts under `data/extracted/m3/`
- Evaluation type: synthetic retrieval guardrails plus local corpus dry-run
- Not evaluated yet: generated repair answers, MCP tool responses, live embedding recall, live rerank quality, FRU graph traversal, dashboard traces

### Baseline Artifacts

M3 extraction produced the local candidate pool:

| Artifact | Local path | M3 count |
|---|---|---:|
| Table records | `data/extracted/m3/tables.jsonl` | 797 |
| Figure records | `data/extracted/m3/figures.jsonl` | 1285 |
| FRU procedures | `data/extracted/m3/fru_procedures.jsonl` | 195 |
| Warning records | `data/extracted/m3/warnings.jsonl` | 687 |
| Dependency edges | `data/extracted/m3/dependency_edges.jsonl` | 535 |

M4 corpus dry-run converted the searchable record types into 2964 retrieval chunks:

```powershell
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --dry-run
```

Result:

```json
{
  "bm25_doc_count": 0,
  "chunk_count": 2964,
  "collection": "thinkpad_m4",
  "dry_run": true,
  "embedded_count": 0,
  "vector_count": 0
}
```

Because this was dry-run, `bm25_doc_count`, `embedded_count`, and `vector_count` are expected to be zero.

### Synthetic Retrieval Checks

Command:

```powershell
.\.venv\Scripts\python -m pytest tests\thinkpad -q
```

Result: passed, 42 tests.

M4-specific assertions:

- Ambiguous high-risk query `X1 Carbon battery removal` returns `clarification_needed=True`.
- Resolved query `X1 Carbon Gen 9 battery removal` filters wrong-generation manual results.
- Domain rerank boosts exact machine type/manual matches.
- Exact error-code query boosts structured error-code table records.
- Procedure queries boost `fru_procedure` records.
- Warning/safety queries boost `warning` records.
- Cited records are preferred over uncited records.

### Provider Checks

Command:

```powershell
.\.venv\Scripts\python -m pytest tests\unit\test_dashscope_providers.py -q
```

Result: passed, 5 tests.

Provider tests use mocked HTTP and do not require live credentials. They validate payload shape, response parsing, factory registration, and missing-key errors for:

- `text-embedding-v4`
- `qwen3-rerank`
- `qwen3.5-flash`

### Current Metrics

| Metric | Status |
|---|---|
| Chunk build count | 2964 dry-run chunks |
| Hit@K | Not measured yet |
| MRR | Not measured yet |
| Citation accuracy | Guardrail-tested synthetically, not measured on a golden set |
| Model/generation accuracy | Resolver unit-tested, not measured on full query set |
| Safety-warning recall | Rerank boost tested synthetically, not measured on golden set |
| Live rerank quality | Not run |
| Answer faithfulness | Out of M4 scope |

### Planned M4 Live Evaluation

Run only after explicitly setting `DASHSCOPE_API_KEY` in the local shell:

```powershell
$env:DASHSCOPE_API_KEY = "<set in local shell only>"
.\.venv\Scripts\python scripts\thinkpad_build_retrieval_index.py --extracted-dir data\extracted\m3 --collection thinkpad_m4 --limit 50
```

Then run representative JSON retrieval queries:

```powershell
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "X1 Carbon battery removal" --collection thinkpad_m4
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "X1 Carbon Gen 9 battery removal" --collection thinkpad_m4
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "21CB battery removal" --collection thinkpad_m4
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "error code 0271" --collection thinkpad_m4
.\.venv\Scripts\python scripts\thinkpad_query_retrieval.py "battery safety warning" --collection thinkpad_m4
```

Live query outputs should be stored under ignored local evaluation artifacts, not committed.

### Interpretation

M4 proves that the project now has:

- Provider wiring for DashScope embedding, rerank, and LLM calls.
- A citation-backed local retrieval corpus over M3 structured artifacts.
- A local index builder with dry-run mode.
- A retrieval facade that enforces model clarification and domain rerank guardrails.

M4 does not prove final answer correctness. M5 should add MCP tool contracts only after live index validation and a small golden retrieval set are recorded.
