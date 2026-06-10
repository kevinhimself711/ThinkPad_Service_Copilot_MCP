"""Domain records for ThinkPad HMM extraction, retrieval, and tool grounding."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class DomainModelError(ValueError):
    """Raised when a ThinkPad domain record violates required invariants."""


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not str(value).strip():
        raise DomainModelError(f"{field_name} cannot be empty")


def _require_list(value: list[str], field_name: str) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DomainModelError(f"{field_name} must be a list of strings")


@dataclass(frozen=True)
class Citation:
    """Page-level source grounding for every authoritative HMM response."""

    manual_id: str
    source_url: str
    page_start: int
    page_end: int | None = None
    section: str | None = None
    section_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.manual_id, "manual_id")
        _require_non_empty(self.source_url, "source_url")
        if self.page_start < 1:
            raise DomainModelError("page_start must be >= 1")
        if self.page_end is not None and self.page_end < self.page_start:
            raise DomainModelError("page_end must be >= page_start")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class TableRecord:
    """Structured row extracted from HMM diagnostic, FRU, or screw-spec tables."""

    record_id: str
    manual_id: str
    page: int
    table_type: str
    columns: list[str]
    row: dict[str, str]
    citation: Citation
    parent_section: str | None = None
    source_url: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.record_id, "record_id")
        _require_non_empty(self.manual_id, "manual_id")
        _require_non_empty(self.table_type, "table_type")
        _require_list(self.columns, "columns")
        if self.page < 1:
            raise DomainModelError("page must be >= 1")
        if not isinstance(self.row, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in self.row.items()
        ):
            raise DomainModelError("row must be a dict[str, str]")
        if self.citation.manual_id != self.manual_id:
            raise DomainModelError("citation.manual_id must match record manual_id")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class FigureRecord:
    """Diagram or page-render reference linked to HMM text and citations."""

    image_id: str
    manual_id: str
    page: int
    citation: Citation
    caption: str = ""
    surrounding_text: str = ""
    related_fru_id: str | None = None
    related_component: str | None = None
    storage_uri: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    source_url: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.image_id, "image_id")
        _require_non_empty(self.manual_id, "manual_id")
        if self.page < 1:
            raise DomainModelError("page must be >= 1")
        if self.citation.manual_id != self.manual_id:
            raise DomainModelError("citation.manual_id must match figure manual_id")
        if self.bbox is not None and len(self.bbox) != 4:
            raise DomainModelError("bbox must contain four float coordinates")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class WarningRecord:
    """Safety warning marker extracted from an HMM page or section."""

    warning_id: str
    manual_id: str
    warning_level: str
    text: str
    citation: Citation
    page: int
    related_component: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.warning_id, "warning_id")
        _require_non_empty(self.manual_id, "manual_id")
        _require_non_empty(self.warning_level, "warning_level")
        _require_non_empty(self.text, "text")
        if self.page < 1:
            raise DomainModelError("page must be >= 1")
        if self.citation.manual_id != self.manual_id:
            raise DomainModelError("citation.manual_id must match warning manual_id")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class FRUProcedure:
    """FRU removal or replacement procedure with prerequisite and warning signals."""

    procedure_id: str
    manual_id: str
    fru_id: str
    fru_name: str
    citation: Citation
    steps: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    warnings: list[WarningRecord] = field(default_factory=list)
    related_image_ids: list[str] = field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.procedure_id, "procedure_id")
        _require_non_empty(self.manual_id, "manual_id")
        _require_non_empty(self.fru_id, "fru_id")
        _require_non_empty(self.fru_name, "fru_name")
        _require_list(self.steps, "steps")
        _require_list(self.prerequisites, "prerequisites")
        _require_list(self.related_image_ids, "related_image_ids")
        if self.citation.manual_id != self.manual_id:
            raise DomainModelError("citation.manual_id must match procedure manual_id")
        if self.page_start is not None and self.page_start < 1:
            raise DomainModelError("page_start must be >= 1")
        if self.page_end is not None and self.page_start is not None and self.page_end < self.page_start:
            raise DomainModelError("page_end must be >= page_start")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class DependencyEdge:
    """Directed prerequisite relationship between two FRU procedures."""

    manual_id: str
    source_fru_id: str
    required_fru_id: str
    citation: Citation
    relation_type: str = "FRU_REQUIRES_PREREQUISITE_FRU"

    def __post_init__(self) -> None:
        _require_non_empty(self.manual_id, "manual_id")
        _require_non_empty(self.source_fru_id, "source_fru_id")
        _require_non_empty(self.required_fru_id, "required_fru_id")
        _require_non_empty(self.relation_type, "relation_type")
        if self.citation.manual_id != self.manual_id:
            raise DomainModelError("citation.manual_id must match dependency manual_id")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class ModelCandidate:
    """A candidate model/manual match returned by the ThinkPad model resolver."""

    canonical_model: str
    manual_id: str
    confidence: float
    matched_on: list[str]
    generations: list[str] = field(default_factory=list)
    machine_types: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_non_empty(self.canonical_model, "canonical_model")
        _require_non_empty(self.manual_id, "manual_id")
        _require_list(self.matched_on, "matched_on")
        _require_list(self.generations, "generations")
        _require_list(self.machine_types, "machine_types")
        if not 0.0 <= self.confidence <= 1.0:
            raise DomainModelError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class ModelResolution:
    """Resolver output for free-form ThinkPad model text."""

    query: str
    candidates: list[ModelCandidate] = field(default_factory=list)
    clarification_needed: bool = False
    reason: str | None = None
    machine_type_candidates: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_non_empty(self.query, "query")
        _require_list(self.machine_type_candidates, "machine_type_candidates")

    @property
    def best_candidate(self) -> ModelCandidate | None:
        """Return the highest-confidence candidate, if present."""

        if not self.candidates:
            return None
        return sorted(self.candidates, key=lambda candidate: candidate.confidence, reverse=True)[0]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)
