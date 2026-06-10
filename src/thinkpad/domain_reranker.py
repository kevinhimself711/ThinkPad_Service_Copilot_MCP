"""Deterministic ThinkPad domain reranking rules."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.core.types import RetrievalResult
from src.thinkpad.models import ModelResolution


@dataclass(frozen=True)
class DomainRerankDecision:
    """Debug metadata for one domain rerank adjustment."""

    chunk_id: str
    original_score: float
    domain_score: float
    boosts: list[str]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation."""

        return {
            "chunk_id": self.chunk_id,
            "original_score": self.original_score,
            "domain_score": self.domain_score,
            "boosts": list(self.boosts),
        }


def rerank_thinkpad_results(
    query: str,
    results: list[RetrievalResult],
    model_resolution: ModelResolution | None = None,
    top_k: int | None = None,
) -> tuple[list[RetrievalResult], list[DomainRerankDecision]]:
    """Apply deterministic ThinkPad-specific reranking rules."""

    query_norm = _normalize(query)
    allowed_manual_ids = _allowed_manual_ids(model_resolution)
    machine_type_candidates = {
        _normalize(machine_type)
        for machine_type in (model_resolution.machine_type_candidates if model_resolution else [])
    }
    scored: list[tuple[float, RetrievalResult, list[str]]] = []

    for result in results:
        score = float(result.score)
        boosts: list[str] = []
        metadata = result.metadata or {}

        manual_id = str(metadata.get("manual_id", ""))
        if allowed_manual_ids:
            if manual_id in allowed_manual_ids:
                score += 0.45
                boosts.append("manual_match")
            else:
                score -= 1.0
                boosts.append("wrong_manual_penalty")

        metadata_machine_types = _split_csv(metadata.get("machine_types"))
        if machine_type_candidates and metadata_machine_types & machine_type_candidates:
            score += 0.35
            boosts.append("machine_type_match")

        record_type = str(metadata.get("record_type", ""))
        table_type = str(metadata.get("table_type", ""))
        if _wants_error(query_norm) and record_type == "table" and table_type == "error_code":
            score += 0.45
            boosts.append("error_table_boost")
        if _wants_screw(query_norm) and record_type == "table":
            score += 0.35
            boosts.append("table_screw_boost")
        if _wants_warning(query_norm) and record_type == "warning":
            score += 0.4
            boosts.append("warning_boost")
        if _wants_figure(query_norm) and record_type == "figure":
            score += 0.35
            boosts.append("figure_boost")
        if _wants_procedure(query_norm) and record_type == "fru_procedure":
            score += 0.35
            boosts.append("procedure_boost")

        exact_codes = _numeric_tokens(query_norm)
        section_id = _normalize(str(metadata.get("section_id", "")))
        fru_id = _normalize(str(metadata.get("fru_id", "")))
        if exact_codes and (section_id in exact_codes or fru_id in exact_codes):
            score += 0.4
            boosts.append("exact_numeric_id_match")
        elif exact_codes and any(code in _normalize(result.text) for code in exact_codes):
            score += 0.2
            boosts.append("exact_numeric_text_match")

        if metadata.get("page_start") and metadata.get("source_url"):
            score += 0.05
            boosts.append("citation_present")

        reranked = RetrievalResult(
            chunk_id=result.chunk_id,
            score=score,
            text=result.text,
            metadata={
                **metadata,
                "original_score": result.score,
                "domain_score": score,
                "domain_boosts": ",".join(boosts),
            },
        )
        scored.append((score, reranked, boosts))

    scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
    limited = scored[:top_k] if top_k is not None else scored
    decisions = [
        DomainRerankDecision(
            chunk_id=result.chunk_id,
            original_score=float(result.metadata.get("original_score", result.score)),
            domain_score=score,
            boosts=boosts,
        )
        for score, result, boosts in limited
    ]
    return [result for _, result, _ in limited], decisions


def _allowed_manual_ids(model_resolution: ModelResolution | None) -> set[str]:
    if not model_resolution or model_resolution.clarification_needed:
        return set()
    return {candidate.manual_id for candidate in model_resolution.candidates}


def _split_csv(value: object) -> set[str]:
    if value is None:
        return set()
    return {_normalize(part) for part in str(value).split(",") if part.strip()}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _numeric_tokens(query_norm: str) -> set[str]:
    return set(re.findall(r"\b[0-9]{3,4}\b", query_norm))


def _wants_error(query_norm: str) -> bool:
    return any(term in query_norm for term in ("error", "code", "beep", "0271", "post"))


def _wants_screw(query_norm: str) -> bool:
    return any(term in query_norm for term in ("screw", "torque", "m2", "mm", "nm"))


def _wants_warning(query_norm: str) -> bool:
    return any(term in query_norm for term in ("warning", "danger", "caution", "battery", "esd", "safety"))


def _wants_figure(query_norm: str) -> bool:
    return any(term in query_norm for term in ("figure", "diagram", "image", "drawing"))


def _wants_procedure(query_norm: str) -> bool:
    return any(
        term in query_norm
        for term in ("remove", "removal", "replace", "replacement", "procedure", "disassemble")
    )
