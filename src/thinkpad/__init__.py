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
from src.thinkpad.retrieval import ThinkPadRetrievalResponse, retrieve_thinkpad
from src.thinkpad.retrieval_corpus import ThinkPadRetrievalChunk, build_retrieval_chunks
from src.thinkpad.retrieval_index import RetrievalIndexBuildResult, build_thinkpad_retrieval_index
from src.thinkpad.tool_service import ThinkPadToolService, ThinkPadToolServiceError

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
    "RetrievalIndexBuildResult",
    "TableRecord",
    "ThinkPadRetrievalChunk",
    "ThinkPadRetrievalResponse",
    "ThinkPadToolService",
    "ThinkPadToolServiceError",
    "WarningRecord",
    "build_retrieval_chunks",
    "build_thinkpad_retrieval_index",
    "extract_manual_artifacts",
    "load_manifest",
    "retrieve_thinkpad",
    "resolve_thinkpad_model",
]
