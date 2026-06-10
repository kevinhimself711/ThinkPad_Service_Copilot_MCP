"""ThinkPad HMM domain utilities for the Service Copilot project."""

from src.thinkpad.extraction import ExtractionOptions, extract_manual_artifacts
from src.thinkpad.manifest import ManifestError, ManualMetadata, load_manifest
from src.thinkpad.model_resolver import resolve_thinkpad_model
from src.thinkpad.models import (
    Citation,
    DependencyEdge,
    DomainModelError,
    ExtractionResult,
    FigureRecord,
    FRUProcedure,
    HMMPage,
    ModelCandidate,
    ModelResolution,
    TableRecord,
    WarningRecord,
)

__all__ = [
    "Citation",
    "DependencyEdge",
    "DomainModelError",
    "ExtractionOptions",
    "ExtractionResult",
    "FigureRecord",
    "FRUProcedure",
    "HMMPage",
    "ManifestError",
    "ManualMetadata",
    "ModelCandidate",
    "ModelResolution",
    "TableRecord",
    "WarningRecord",
    "extract_manual_artifacts",
    "load_manifest",
    "resolve_thinkpad_model",
]
