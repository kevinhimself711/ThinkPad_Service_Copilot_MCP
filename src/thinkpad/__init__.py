"""ThinkPad HMM domain utilities for the Service Copilot project."""

from src.thinkpad.agent import (
    AgentRefusal,
    EvidenceBundle,
    RepairPlanRequest,
    RepairPlanResult,
    RepairPlanStep,
    ToolCallTrace,
    plan_thinkpad_repair,
)
from src.thinkpad.agent_evaluation import (
    ThinkPadAgentEvalReport,
    ThinkPadAgentEvalResult,
    ThinkPadAgentGoldenCase,
    evaluate_thinkpad_agent_cases,
    load_thinkpad_agent_golden_set,
)
from src.thinkpad.evaluation import (
    ThinkPadEvalReport,
    ThinkPadEvalResult,
    ThinkPadGoldenCase,
    evaluate_thinkpad_cases,
    load_thinkpad_golden_set,
)
from src.thinkpad.extraction import ExtractionOptions, extract_manual_artifacts
from src.thinkpad.fru_graph import FRUDependencyGraph, build_fru_dependency_graph
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
    "AgentRefusal",
    "Citation",
    "DependencyEdge",
    "DomainModelError",
    "EvidenceBundle",
    "ExtractionOptions",
    "ExtractionResult",
    "FigureRecord",
    "FRUProcedure",
    "FRUDependencyGraph",
    "HMMPage",
    "ManifestError",
    "ManualMetadata",
    "ModelCandidate",
    "ModelResolution",
    "RetrievalIndexBuildResult",
    "RepairPlanRequest",
    "RepairPlanResult",
    "RepairPlanStep",
    "TableRecord",
    "ThinkPadAgentEvalReport",
    "ThinkPadAgentEvalResult",
    "ThinkPadAgentGoldenCase",
    "ThinkPadEvalReport",
    "ThinkPadEvalResult",
    "ThinkPadGoldenCase",
    "ThinkPadRetrievalChunk",
    "ThinkPadRetrievalResponse",
    "ThinkPadToolService",
    "ThinkPadToolServiceError",
    "ToolCallTrace",
    "WarningRecord",
    "build_retrieval_chunks",
    "build_thinkpad_retrieval_index",
    "build_fru_dependency_graph",
    "evaluate_thinkpad_agent_cases",
    "evaluate_thinkpad_cases",
    "extract_manual_artifacts",
    "load_manifest",
    "load_thinkpad_agent_golden_set",
    "load_thinkpad_golden_set",
    "plan_thinkpad_repair",
    "retrieve_thinkpad",
    "resolve_thinkpad_model",
]
