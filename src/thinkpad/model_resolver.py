"""Rule-based ThinkPad model resolver for manifest-backed manuals."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import ModelCandidate, ModelResolution

_ORDINAL_GENERATIONS = {
    "first": "1",
    "second": "2",
    "third": "3",
    "fourth": "4",
    "fifth": "5",
    "sixth": "6",
    "seventh": "7",
    "eighth": "8",
    "ninth": "9",
    "tenth": "10",
}


@dataclass(frozen=True)
class _ModelParts:
    canonical_model: str
    base: str
    generation: str | None


def resolve_thinkpad_model(query: str, manuals: list[ManualMetadata]) -> ModelResolution:
    """Resolve free-form ThinkPad model text against a validated manifest.

    The resolver is intentionally conservative: exact machine type wins, explicit
    model + generation is accepted, and generationless family names are returned
    as clarification candidates rather than guessed.
    """

    if not query.strip():
        raise ValueError("query cannot be empty")

    normalized_query = _normalize_text(query)
    machine_type_matches = _match_machine_types(normalized_query, manuals)
    if machine_type_matches:
        candidates = _dedupe_candidates(machine_type_matches)
        return ModelResolution(
            query=query,
            candidates=candidates,
            clarification_needed=False,
            reason="exact_machine_type_match",
            machine_type_candidates=_candidate_machine_types(candidates),
        )

    exact_candidates: list[ModelCandidate] = []
    broad_candidates: list[ModelCandidate] = []

    for manual in manuals:
        for model in manual.models:
            parts = _split_model(model)
            if not _contains_phrase(normalized_query, parts.base):
                continue

            if parts.generation and _contains_generation(normalized_query, parts.generation):
                exact_candidates.append(
                    _candidate(
                        manual=manual,
                        canonical_model=parts.canonical_model,
                        confidence=0.92,
                        matched_on=[f"model:{parts.base}", f"generation:{parts.generation}"],
                    )
                )
            elif parts.generation is None and _contains_phrase(normalized_query, parts.base):
                exact_candidates.append(
                    _candidate(
                        manual=manual,
                        canonical_model=parts.canonical_model,
                        confidence=0.9,
                        matched_on=[f"model:{parts.base}"],
                    )
                )
            else:
                broad_candidates.append(
                    _candidate(
                        manual=manual,
                        canonical_model=parts.canonical_model,
                        confidence=0.55,
                        matched_on=[f"model_family:{parts.base}"],
                    )
                )

    if exact_candidates:
        candidates = _dedupe_candidates(exact_candidates)
        return ModelResolution(
            query=query,
            candidates=candidates,
            clarification_needed=len(candidates) > 1 and _has_multiple_generations(candidates),
            reason="model_generation_match",
            machine_type_candidates=_candidate_machine_types(candidates),
        )

    if broad_candidates:
        candidates = _dedupe_candidates(broad_candidates)
        return ModelResolution(
            query=query,
            candidates=candidates,
            clarification_needed=True,
            reason="generation_required",
            machine_type_candidates=_candidate_machine_types(candidates),
        )

    return ModelResolution(
        query=query,
        candidates=[],
        clarification_needed=True,
        reason="unsupported_model",
        machine_type_candidates=[],
    )


def _match_machine_types(normalized_query: str, manuals: list[ManualMetadata]) -> list[ModelCandidate]:
    tokens = set(normalized_query.split())
    candidates: list[ModelCandidate] = []
    for manual in manuals:
        matched_machine_types = [
            machine_type
            for machine_type in manual.machine_types
            if _normalize_text(machine_type) in tokens
        ]
        if not matched_machine_types:
            continue
        for model in manual.models:
            candidates.append(
                _candidate(
                    manual=manual,
                    canonical_model=model,
                    confidence=0.98,
                    matched_on=[f"machine_type:{machine_type}" for machine_type in matched_machine_types],
                    machine_types=matched_machine_types,
                )
            )
    return candidates


def _candidate(
    manual: ManualMetadata,
    canonical_model: str,
    confidence: float,
    matched_on: list[str],
    machine_types: list[str] | None = None,
) -> ModelCandidate:
    return ModelCandidate(
        canonical_model=canonical_model,
        manual_id=manual.manual_id,
        confidence=confidence,
        matched_on=matched_on,
        generations=list(manual.generations),
        machine_types=list(machine_types or manual.machine_types),
    )


def _dedupe_candidates(candidates: list[ModelCandidate]) -> list[ModelCandidate]:
    best_by_key: dict[tuple[str, str], ModelCandidate] = {}
    for candidate in candidates:
        key = (candidate.canonical_model, candidate.manual_id)
        existing = best_by_key.get(key)
        if existing is None or candidate.confidence > existing.confidence:
            best_by_key[key] = candidate
    return sorted(
        best_by_key.values(),
        key=lambda candidate: (-candidate.confidence, candidate.canonical_model, candidate.manual_id),
    )


def _candidate_machine_types(candidates: list[ModelCandidate]) -> list[str]:
    values = {machine_type for candidate in candidates for machine_type in candidate.machine_types}
    return sorted(values)


def _has_multiple_generations(candidates: list[ModelCandidate]) -> bool:
    generations = {
        generation
        for candidate in candidates
        for generation in candidate.generations
        if generation
    }
    return len(generations) > 1


def _split_model(model: str) -> _ModelParts:
    normalized = _drop_thinkpad_prefix(_normalize_text(model))
    generation_match = re.search(r"\bgen ([0-9]+)\b", normalized)
    generation = generation_match.group(1) if generation_match else None
    base = re.sub(r"\bgen [0-9]+\b", " ", normalized)
    base = re.sub(r"\s+", " ", base).strip()
    return _ModelParts(canonical_model=model, base=base, generation=generation)


def _contains_generation(normalized_query: str, generation: str) -> bool:
    return _contains_phrase(normalized_query, f"gen {generation}")


def _contains_phrase(normalized_query: str, normalized_phrase: str) -> bool:
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {normalized_query} "


def _normalize_text(value: str) -> str:
    normalized = value.lower()
    normalized = normalized.replace("&", " and ")
    for word, generation in _ORDINAL_GENERATIONS.items():
        normalized = re.sub(rf"\b{word}\s+gen(?:eration)?\b", f"gen {generation}", normalized)
    normalized = re.sub(r"\b([0-9]+)(st|nd|rd|th)\s+gen(?:eration)?\b", r"gen \1", normalized)
    normalized = re.sub(r"\bgen\s*([0-9]+)\b", r"gen \1", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _drop_thinkpad_prefix(value: str) -> str:
    return re.sub(r"^thinkpad\s+", "", value).strip()
