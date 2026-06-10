"""ThinkPad HMM domain utilities for the Service Copilot project."""

from src.thinkpad.manifest import ManifestError, ManualMetadata, load_manifest
from src.thinkpad.model_resolver import resolve_thinkpad_model
from src.thinkpad.models import (
    Citation,
    DependencyEdge,
    DomainModelError,
    FigureRecord,
    FRUProcedure,
    ModelCandidate,
    ModelResolution,
    TableRecord,
    WarningRecord,
)

__all__ = [
    "Citation",
    "DependencyEdge",
    "DomainModelError",
    "FigureRecord",
    "FRUProcedure",
    "ManifestError",
    "ManualMetadata",
    "ModelCandidate",
    "ModelResolution",
    "TableRecord",
    "WarningRecord",
    "load_manifest",
    "resolve_thinkpad_model",
]
