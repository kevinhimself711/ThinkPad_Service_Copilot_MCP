# M0 Baseline

## Scope

M0 bootstraps ThinkPad Service Copilot MCP from the upstream modular RAG MCP server. It does not download Lenovo HMM PDFs, build ThinkPad domain modules, ingest manuals, create vector stores, or commit copyrighted manual content.

## Upstream

- Upstream repository: https://github.com/jerry-ai-dev/MODULAR-RAG-MCP-SERVER
- Upstream baseline branch: `main`
- Upstream baseline commit: `f658c5a4011c8b826707a65a3b11ce9301b0626f`
- Upstream baseline commit message: `feat: Modular RAG MCP Server - Complete implementation with MCP tools, ingestion pipeline, hybrid search, dashboard, evaluation system, and agent skills`

## GitHub Target

- GitHub account: `kevinhimself711`
- Target repository: `kevinhimself711/ThinkPad_Service_Copilot_MCP`
- Visibility: public
- Development branch: `thinkpad-hmm-domain`

## Local Notes

- GitHub CLI authentication was confirmed for `kevinhimself711`.
- The Windows `py` launcher was not available in this shell; validation used `python` directly.
- Local Python version: `Python 3.12.7`.
- Direct `git fetch` over HTTPS to `github.com` failed from this shell during M0 with connection timeouts, although GitHub API access worked.
- To preserve upstream history remotely, M0 uses a GitHub fork of the upstream repository and creates the ThinkPad bootstrap commit through GitHub's Git Data API.
- The local workspace was populated from the upstream `main` zip archive for validation and file preparation.

## Validation Commands

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest tests/unit/test_smoke_imports.py
```

## Validation Results

- `python -m venv .venv`: passed.
- `.venv\Scripts\python -m pip install -U pip`: passed.
- `.venv\Scripts\pip install -e ".[dev]"`: passed.
- `.venv\Scripts\python -m pytest tests/unit/test_smoke_imports.py`: passed, `22 passed in 1.50s`.
