"""Service layer backing ThinkPad-specific MCP tools.

M5 exposes evidence records through MCP. This module keeps file loading,
model resolution, exact structured lookups, and retrieval facade calls outside
the protocol handlers so the handlers stay thin and testable.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.core.settings import REPO_ROOT, Settings, load_settings, resolve_path
from src.thinkpad.manifest import ManualMetadata, load_manifest
from src.thinkpad.model_resolver import resolve_thinkpad_model as resolve_model
from src.thinkpad.retrieval import retrieve_thinkpad

ToolResponse = dict[str, Any]
Retriever = Callable[..., Any]


class ThinkPadToolServiceError(RuntimeError):
    """Raised when ThinkPad tool service setup fails."""


class ThinkPadToolService:
    """Application service for ThinkPad MCP evidence tools."""

    def __init__(
        self,
        manifest_path: str | Path | None = None,
        extracted_dir: str | Path | None = None,
        settings: Settings | None = None,
        manuals: list[ManualMetadata] | None = None,
        tables: list[dict[str, Any]] | None = None,
        fru_procedures: list[dict[str, Any]] | None = None,
        figures: list[dict[str, Any]] | None = None,
        warnings: list[dict[str, Any]] | None = None,
        retriever: Retriever | None = None,
    ) -> None:
        self.manifest_path = resolve_path(manifest_path or _default_manifest_path())
        self.extracted_dir = resolve_path(extracted_dir or "data/extracted/m3")
        self._settings = settings
        self._manuals = list(manuals) if manuals is not None else None
        self._tables = list(tables) if tables is not None else None
        self._fru_procedures = list(fru_procedures) if fru_procedures is not None else None
        self._figures = list(figures) if figures is not None else None
        self._warnings = list(warnings) if warnings is not None else None
        self._retriever = retriever or retrieve_thinkpad

    @property
    def manuals(self) -> list[ManualMetadata]:
        """Return manifest-backed manual metadata."""

        if self._manuals is None:
            self._manuals = load_manifest(self.manifest_path)
        return self._manuals

    @property
    def settings(self) -> Settings:
        """Return application settings, loading lazily."""

        if self._settings is None:
            self._settings = load_settings()
        return self._settings

    @property
    def tables(self) -> list[dict[str, Any]]:
        """Return structured table records from M3 JSONL."""

        if self._tables is None:
            self._tables = _read_jsonl(self.extracted_dir / "tables.jsonl")
        return self._tables

    @property
    def fru_procedures(self) -> list[dict[str, Any]]:
        """Return structured FRU procedure records from M3 JSONL."""

        if self._fru_procedures is None:
            self._fru_procedures = _read_jsonl(self.extracted_dir / "fru_procedures.jsonl")
        return self._fru_procedures

    @property
    def figures(self) -> list[dict[str, Any]]:
        """Return figure metadata records from M3 JSONL."""

        if self._figures is None:
            self._figures = _read_jsonl(self.extracted_dir / "figures.jsonl")
        return self._figures

    @property
    def warnings(self) -> list[dict[str, Any]]:
        """Return safety warning records from M3 JSONL."""

        if self._warnings is None:
            self._warnings = _read_jsonl(self.extracted_dir / "warnings.jsonl")
        return self._warnings

    def list_supported_models(self, include_machine_types: bool = True) -> ToolResponse:
        """List supported models and backing HMM manuals."""

        results: list[dict[str, Any]] = []
        for manual in self.manuals:
            item = {
                "manual_id": manual.manual_id,
                "title": manual.title,
                "models": list(manual.models),
                "generations": list(manual.generations),
                "source_url": manual.source_url,
                "product_page_url": manual.product_page_url,
                "page_count": manual.page_count,
                "year": manual.year,
            }
            if include_machine_types:
                item["machine_types"] = list(manual.machine_types)
            results.append(item)

        return _response(
            tool="list_supported_models",
            status="ok",
            message=f"{len(results)} ThinkPad HMM manuals are configured.",
            results=results,
            metadata={"manual_count": len(results)},
        )

    def resolve_thinkpad_model(self, query: str) -> ToolResponse:
        """Resolve free-form model text against the manifest."""

        if not query or not query.strip():
            return _error("resolve_thinkpad_model", "query cannot be empty")
        resolution = resolve_model(query, self.manuals)
        status = "clarification_required" if resolution.clarification_needed else "ok"
        return _response(
            tool="resolve_thinkpad_model",
            status=status,
            clarification_needed=resolution.clarification_needed,
            message=resolution.reason or "",
            model_resolution=resolution.to_dict(),
            results=[candidate.to_dict() for candidate in resolution.candidates],
            metadata={"candidate_count": len(resolution.candidates)},
        )

    def query_thinkpad_service(
        self,
        query: str,
        top_k: int = 5,
        collection: str = "thinkpad_m4",
    ) -> ToolResponse:
        """Run the M4 retrieval facade and return evidence JSON."""

        if not query or not query.strip():
            return _error("query_thinkpad_service", "query cannot be empty")
        try:
            retrieval_response = self._retriever(
                query=query,
                manuals=self.manuals,
                settings=self.settings,
                collection=collection,
                top_k=top_k,
            )
            data = retrieval_response.to_dict()
        except Exception as exc:
            return _error(
                "query_thinkpad_service",
                f"retrieval failed: {exc}",
                metadata={"collection": collection, "top_k": top_k},
            )

        status = "ok"
        if data.get("clarification_needed"):
            status = "clarification_required"
        elif not data.get("results"):
            status = "not_found"

        return _response(
            tool="query_thinkpad_service",
            status=status,
            clarification_needed=bool(data.get("clarification_needed")),
            message=data.get("reason") or "",
            model_resolution=data.get("model_resolution") or {},
            results=data.get("results") or [],
            citations=_citations_from_results(data.get("results") or []),
            metadata={
                "collection": collection,
                "top_k": top_k,
                "domain_rerank": data.get("domain_rerank") or [],
                "rerank_fallback": bool(data.get("rerank_fallback")),
            },
        )

    def lookup_error_code(
        self,
        error_code: str,
        model: str | None = None,
        top_k: int = 5,
    ) -> ToolResponse:
        """Look up exact error-code rows from structured table records."""

        if not error_code or not error_code.strip():
            return _error("lookup_error_code", "error_code cannot be empty")
        guard = self._model_guard("lookup_error_code", model, required=False)
        if guard["response"] is not None:
            return guard["response"]

        code = error_code.strip()
        candidates = [
            record
            for record in self.tables
            if _manual_allowed(record, guard["allowed_manual_ids"])
            and _contains_exact_code(_record_text(record), code)
        ]
        candidates.sort(key=lambda record: 0 if record.get("table_type") == "error_code" else 1)
        results = [_table_result(record) for record in candidates[:top_k]]
        return _lookup_response(
            tool="lookup_error_code",
            results=results,
            model_resolution=guard["model_resolution"],
            not_found_message=f"No structured table row found for error code {code}.",
        )

    def get_screw_spec(
        self,
        model: str,
        component_or_screw: str,
        top_k: int = 5,
    ) -> ToolResponse:
        """Look up screw or torque table rows without inferring missing values."""

        if not component_or_screw or not component_or_screw.strip():
            return _error("get_screw_spec", "component_or_screw cannot be empty")
        guard = self._model_guard("get_screw_spec", model, required=True)
        if guard["response"] is not None:
            return guard["response"]

        query = component_or_screw.strip()
        candidates = [
            record
            for record in self.tables
            if _manual_allowed(record, guard["allowed_manual_ids"])
            and _contains_text(_record_text(record), query)
        ]
        candidates.sort(key=_screw_rank)
        results = [_table_result(record) for record in candidates[:top_k]]
        return _lookup_response(
            tool="get_screw_spec",
            results=results,
            model_resolution=guard["model_resolution"],
            not_found_message=f"No structured screw-spec row found for {query}.",
        )

    def get_fru_procedure(
        self,
        model: str,
        component_or_fru: str,
        top_k: int = 5,
    ) -> ToolResponse:
        """Return structured FRU procedure candidates for an unambiguous model."""

        if not component_or_fru or not component_or_fru.strip():
            return _error("get_fru_procedure", "component_or_fru cannot be empty")
        guard = self._model_guard("get_fru_procedure", model, required=True)
        if guard["response"] is not None:
            return guard["response"]

        query = component_or_fru.strip()
        candidates = [
            record
            for record in self.fru_procedures
            if _manual_allowed(record, guard["allowed_manual_ids"])
            and _contains_text(_record_text(record), query)
        ]
        candidates.sort(key=lambda record: _fru_rank(record, query))
        results = [_fru_result(record) for record in candidates[:top_k]]
        return _lookup_response(
            tool="get_fru_procedure",
            results=results,
            model_resolution=guard["model_resolution"],
            not_found_message=f"No structured FRU procedure found for {query}.",
        )

    def get_related_diagram(
        self,
        model: str,
        component_or_fru: str,
        top_k: int = 5,
        include_images: bool = False,
    ) -> ToolResponse:
        """Return figure metadata candidates; image bytes are not emitted in M5."""

        if not component_or_fru or not component_or_fru.strip():
            return _error("get_related_diagram", "component_or_fru cannot be empty")
        guard = self._model_guard("get_related_diagram", model, required=True)
        if guard["response"] is not None:
            return guard["response"]

        query = component_or_fru.strip()
        candidates = [
            record
            for record in self.figures
            if _manual_allowed(record, guard["allowed_manual_ids"])
            and _contains_text(_record_text(record), query)
        ]
        candidates.sort(key=lambda record: _figure_rank(record, query))
        results = [_figure_result(record) for record in candidates[:top_k]]
        return _lookup_response(
            tool="get_related_diagram",
            results=results,
            model_resolution=guard["model_resolution"],
            not_found_message=f"No related figure metadata found for {query}.",
            metadata={"include_images_requested": include_images, "image_bytes_returned": False},
        )

    def get_safety_warnings(
        self,
        model: str,
        component: str | None = None,
        top_k: int = 5,
    ) -> ToolResponse:
        """Return cited safety warnings for a model and optional component."""

        guard = self._model_guard("get_safety_warnings", model, required=True)
        if guard["response"] is not None:
            return guard["response"]

        candidates = [
            record
            for record in self.warnings
            if _manual_allowed(record, guard["allowed_manual_ids"])
            and (not component or _contains_text(_record_text(record), component))
        ]
        candidates.sort(key=_warning_rank)
        results = [_warning_result(record) for record in candidates[:top_k]]
        message = "No cited safety warning found."
        if component:
            message = f"No cited safety warning found for {component}."
        return _lookup_response(
            tool="get_safety_warnings",
            results=results,
            model_resolution=guard["model_resolution"],
            not_found_message=message,
        )

    def _model_guard(self, tool: str, model: str | None, required: bool) -> dict[str, Any]:
        if required and (not model or not model.strip()):
            return {
                "response": _error(tool, "model is required"),
                "model_resolution": {},
                "allowed_manual_ids": None,
            }
        if not model or not model.strip():
            return {"response": None, "model_resolution": {}, "allowed_manual_ids": None}

        resolution = resolve_model(model, self.manuals)
        resolution_dict = resolution.to_dict()
        if resolution.clarification_needed:
            return {
                "response": _response(
                    tool=tool,
                    status="clarification_required",
                    clarification_needed=True,
                    message=resolution.reason or "model clarification required",
                    model_resolution=resolution_dict,
                    metadata={"candidate_count": len(resolution.candidates)},
                ),
                "model_resolution": resolution_dict,
                "allowed_manual_ids": None,
            }
        allowed = {candidate.manual_id for candidate in resolution.candidates}
        return {
            "response": None,
            "model_resolution": resolution_dict,
            "allowed_manual_ids": allowed or None,
        }


def _default_manifest_path() -> Path:
    local = REPO_ROOT / "data" / "manifests" / "manuals_manifest.yaml"
    if local.exists():
        return local
    return REPO_ROOT / "config" / "manuals_manifest.example.yaml"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ThinkPadToolServiceError(f"invalid JSONL at {path}:{line_number}") from exc
    return records


def _response(
    tool: str,
    status: str,
    clarification_needed: bool = False,
    message: str = "",
    model_resolution: dict[str, Any] | None = None,
    results: list[dict[str, Any]] | None = None,
    citations: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ToolResponse:
    results = list(results or [])
    citations = list(citations or _citations_from_results(results))
    return {
        "tool": tool,
        "status": status,
        "clarification_needed": clarification_needed,
        "message": message,
        "model_resolution": model_resolution or {},
        "results": results,
        "citations": citations,
        "metadata": metadata or {},
    }


def _error(tool: str, message: str, metadata: dict[str, Any] | None = None) -> ToolResponse:
    return _response(tool=tool, status="error", message=message, metadata=metadata)


def _lookup_response(
    tool: str,
    results: list[dict[str, Any]],
    model_resolution: dict[str, Any],
    not_found_message: str,
    metadata: dict[str, Any] | None = None,
) -> ToolResponse:
    if not results:
        return _response(
            tool=tool,
            status="not_found",
            message=not_found_message,
            model_resolution=model_resolution,
            metadata=metadata,
        )
    return _response(
        tool=tool,
        status="ok",
        message=f"{len(results)} cited candidate record(s) found.",
        model_resolution=model_resolution,
        results=results,
        metadata=metadata or {},
    )


def _citations_from_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for result in results:
        citation = result.get("citation") or _citation_for(result)
        key = (
            citation.get("manual_id"),
            citation.get("source_url"),
            citation.get("page_start"),
            citation.get("page_end"),
            citation.get("section"),
            citation.get("section_id"),
        )
        if key not in seen:
            seen.add(key)
            citations.append(citation)
    return citations


def _citation_for(record: dict[str, Any]) -> dict[str, Any]:
    citation = record.get("citation") or {}
    page_start = citation.get("page_start") or record.get("page_start") or record.get("page")
    page_end = citation.get("page_end") or record.get("page_end") or page_start
    return {
        "manual_id": citation.get("manual_id") or record.get("manual_id"),
        "source_url": citation.get("source_url") or record.get("source_url"),
        "page_start": page_start,
        "page_end": page_end,
        "section": citation.get("section") or record.get("parent_section"),
        "section_id": citation.get("section_id") or record.get("fru_id"),
    }


def _table_result(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record.get("record_id"),
        "manual_id": record.get("manual_id"),
        "record_type": "table",
        "table_type": record.get("table_type"),
        "columns": record.get("columns") or [],
        "row": record.get("row") or {},
        "parent_section": record.get("parent_section"),
        "citation": _citation_for(record),
    }


def _fru_result(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "procedure_id": record.get("procedure_id"),
        "manual_id": record.get("manual_id"),
        "record_type": "fru_procedure",
        "fru_id": record.get("fru_id"),
        "fru_name": record.get("fru_name"),
        "steps": record.get("steps") or [],
        "prerequisites": record.get("prerequisites") or [],
        "warnings": record.get("warnings") or [],
        "related_image_ids": record.get("related_image_ids") or [],
        "citation": _citation_for(record),
    }


def _figure_result(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "image_id": record.get("image_id"),
        "manual_id": record.get("manual_id"),
        "record_type": "figure",
        "caption": record.get("caption") or "",
        "surrounding_text": record.get("surrounding_text") or "",
        "related_fru_id": record.get("related_fru_id"),
        "related_component": record.get("related_component"),
        "storage_uri": record.get("storage_uri"),
        "bbox": record.get("bbox"),
        "citation": _citation_for(record),
    }


def _warning_result(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "warning_id": record.get("warning_id"),
        "manual_id": record.get("manual_id"),
        "record_type": "warning",
        "warning_level": record.get("warning_level"),
        "text": record.get("text"),
        "related_component": record.get("related_component"),
        "citation": _citation_for(record),
    }


def _manual_allowed(record: dict[str, Any], allowed_manual_ids: set[str] | None) -> bool:
    return allowed_manual_ids is None or record.get("manual_id") in allowed_manual_ids


def _record_text(record: dict[str, Any]) -> str:
    return " ".join(_flatten(record)).lower()


def _flatten(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        items: list[str] = []
        for key, nested in value.items():
            items.append(str(key))
            items.extend(_flatten(nested))
        return items
    if isinstance(value, list):
        items = []
        for nested in value:
            items.extend(_flatten(nested))
        return items
    return [str(value)]


def _contains_exact_code(text: str, code: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(code.lower())}(?![A-Za-z0-9])", text) is not None


def _contains_text(text: str, query: str) -> bool:
    normalized_text = _normalize_lookup_text(text)
    terms = [term for term in re.split(r"\s+", _normalize_lookup_text(query)) if term]
    return all(term in normalized_text for term in terms)


def _normalize_lookup_text(value: str) -> str:
    normalized = value.lower()
    normalized = normalized.replace("×", "x").replace("*", "x")
    normalized = re.sub(r"\bm\s*([0-9]+(?:\.[0-9]+)?)\s*x\s*([0-9]+(?:\.[0-9]+)?)\b", r"m\1x\2", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _screw_rank(record: dict[str, Any]) -> tuple[int, str]:
    table_type = record.get("table_type")
    if table_type == "screw_spec":
        return (0, str(record.get("record_id", "")))
    if table_type == "fru":
        return (1, str(record.get("record_id", "")))
    return (2, str(record.get("record_id", "")))


def _fru_rank(record: dict[str, Any], query: str) -> tuple[int, str]:
    normalized_query = query.lower().strip()
    if normalized_query == str(record.get("fru_id", "")).lower():
        return (0, str(record.get("procedure_id", "")))
    if normalized_query in str(record.get("fru_name", "")).lower():
        return (1, str(record.get("procedure_id", "")))
    return (2, str(record.get("procedure_id", "")))


def _figure_rank(record: dict[str, Any], query: str) -> tuple[int, str]:
    normalized_query = query.lower().strip()
    if normalized_query in str(record.get("related_fru_id", "")).lower():
        return (0, str(record.get("image_id", "")))
    if normalized_query in str(record.get("related_component", "")).lower():
        return (1, str(record.get("image_id", "")))
    if normalized_query in str(record.get("caption", "")).lower():
        return (2, str(record.get("image_id", "")))
    return (3, str(record.get("image_id", "")))


def _warning_rank(record: dict[str, Any]) -> tuple[int, str]:
    levels = {"DANGER": 0, "CAUTION": 1, "ESD": 2, "WARNING": 3}
    return (levels.get(str(record.get("warning_level", "")).upper(), 4), str(record.get("warning_id", "")))
