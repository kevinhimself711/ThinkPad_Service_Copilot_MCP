"""Repair-planning agent client for ThinkPad HMM evidence tools.

M8 keeps the agent deliberately small: deterministic tool orchestration first,
optional LLM composition second. The LLM may rewrite evidence into readable
repair prose, but it must not invent repair facts beyond cited tool evidence.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from src.libs.llm.base_llm import BaseLLM, Message
from src.thinkpad.tool_service import ThinkPadToolService


class ThinkPadAgentError(RuntimeError):
    """Raised when the ThinkPad repair-planning agent cannot continue."""


@dataclass(frozen=True)
class RepairPlanRequest:
    """Input request for a ThinkPad repair-planning run."""

    query: str
    collection: str = "thinkpad_m4"
    top_k: int = 5
    use_retrieval: bool = False
    require_live_retrieval: bool = False
    use_llm: bool = False
    llm_repair_attempts: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class ToolCallTrace:
    """One evidence-tool call made by the agent."""

    tool: str
    args: dict[str, Any]
    status: str
    result_count: int = 0
    elapsed_ms: float = 0.0
    citations: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class EvidenceBundle:
    """Grouped evidence returned by ThinkPad tools."""

    model_resolution: dict[str, Any] = field(default_factory=dict)
    procedure: list[dict[str, Any]] = field(default_factory=list)
    dependency_chain: list[dict[str, Any]] = field(default_factory=list)
    error_codes: list[dict[str, Any]] = field(default_factory=list)
    screw_specs: list[dict[str, Any]] = field(default_factory=list)
    diagrams: list[dict[str, Any]] = field(default_factory=list)
    safety_warnings: list[dict[str, Any]] = field(default_factory=list)
    retrieval: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class RepairPlanStep:
    """One cited step in the repair plan."""

    step_id: str
    title: str
    action: str
    evidence_type: str
    citations: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class AgentRefusal:
    """A refusal or clarification result emitted by the agent."""

    reason: str
    message: str
    citations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass(frozen=True)
class RepairPlanResult:
    """Agent result containing trace, evidence, plan, and validation signals."""

    status: str
    clarification_needed: bool
    query: str
    message: str
    request: dict[str, Any]
    tool_trace: list[ToolCallTrace] = field(default_factory=list)
    evidence_bundle: EvidenceBundle = field(default_factory=EvidenceBundle)
    repair_plan: list[RepairPlanStep] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    refusal: AgentRefusal | None = None
    generated_answer: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        data = asdict(self)
        data["refusal"] = self.refusal.to_dict() if self.refusal else None
        return data

    def to_json(self) -> str:
        """Return deterministic JSON."""

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


@dataclass(frozen=True)
class _Intent:
    kind: str
    component: str | None = None
    error_code: str | None = None
    screw_query: str | None = None


_ERROR_CODE_RE = re.compile(r"(?<![A-Za-z0-9])([0-9]{4})(?![A-Za-z0-9])")
_SCREW_RE = re.compile(r"\bm\s*[0-9]+(?:\.[0-9]+)?\s*(?:x|\*|×|脳)\s*[0-9]+(?:\.[0-9]+)?\b", re.IGNORECASE)
_TORQUE_RE = re.compile(r"\b[0-9]+(?:\.[0-9]+)?\s*(?:nm|n m|kgf)\b", re.IGNORECASE)
_FRU_ID_RE = re.compile(r"(?<![A-Za-z0-9])([0-9]{4})(?![A-Za-z0-9])")

_COMPONENT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bsystem board\b", "system board"),
    (r"\bnano[- ]sim\b|\bsim card\b", "Nano-SIM"),
    (r"\bbuilt[- ]in battery\b", "built-in battery"),
    (r"\bremovable battery\b", "removable battery"),
    (r"\bcoin[- ]cell battery\b", "coin-cell battery"),
    (r"\bbattery\b", "battery"),
    (r"\bthermal fan\b|\bfan assembly\b|\bfan\b", "thermal fan assembly"),
    (r"\bbase cover\b", "base cover assembly"),
    (r"\bkeyboard\b", "keyboard"),
    (r"\bspeaker\b", "speaker assembly"),
    (r"\bmemory\b", "memory module"),
    (r"\bm\.?2\s+ssd\b|\bssd\b", "SSD"),
    (r"\bsolid[- ]state drive\b|\bstorage drive\b", "solid-state drive"),
    (r"\bwwan\b|\bwireless[- ]wan\b", "wireless WAN card"),
    (r"\bwlan\b|\bwireless[- ]lan\b", "wireless LAN card"),
    (r"\bdisplay\b|\blcd\b", "display assembly"),
    (r"\baudio board\b", "audio board"),
    (r"\bio card\b|\bi/o card\b", "I/O card"),
    (r"\bio bracket\b|\bi/o bracket\b", "I/O bracket"),
)


def plan_thinkpad_repair(
    query: str,
    service: ThinkPadToolService,
    use_llm: bool = False,
    llm: BaseLLM | None = None,
    collection: str = "thinkpad_m4",
    top_k: int = 5,
    use_retrieval: bool = False,
    require_live_retrieval: bool = False,
    llm_repair_attempts: int = 1,
) -> RepairPlanResult:
    """Plan a ThinkPad repair workflow from citation-backed evidence tools."""

    request = RepairPlanRequest(
        query=query,
        collection=collection,
        top_k=top_k,
        use_retrieval=use_retrieval or require_live_retrieval,
        require_live_retrieval=require_live_retrieval,
        use_llm=use_llm,
        llm_repair_attempts=max(0, llm_repair_attempts),
    )
    if not query or not query.strip():
        return _final_result(
            status="error",
            clarification_needed=False,
            query=query,
            message="query cannot be empty",
            request=request,
            tool_trace=[],
            evidence=EvidenceBundle(),
            repair_plan=[],
            refusal=None,
            generated_answer=None,
            validation={"provider_error": False, "unsupported_claims": []},
        )

    calls: list[ToolCallTrace] = []
    evidence = EvidenceBundle()
    intent = _detect_intent(query)

    resolve_response, trace = _call_tool(
        "resolve_thinkpad_model",
        service.resolve_thinkpad_model,
        {"query": query},
    )
    calls.append(trace)
    evidence = _replace_evidence(evidence, model_resolution=resolve_response.get("model_resolution") or {})

    unsupported = _is_unsupported_resolution(resolve_response)
    if unsupported:
        if _is_broad_thinkpad_query(query):
            refusal = AgentRefusal(
                reason="model_clarification_required",
                message="Model generation or machine type is required before returning a unique repair plan.",
            )
            return _final_result(
                status="clarification_required",
                clarification_needed=True,
                query=query,
                message=refusal.message,
                request=request,
                tool_trace=calls,
                evidence=evidence,
                repair_plan=[],
                refusal=refusal,
                generated_answer=None,
                validation={"provider_error": False, "unsupported_claims": []},
            )
        refusal = AgentRefusal(
            reason="unsupported_model",
            message=resolve_response.get("message") or "The model is not supported by the local HMM manifest.",
        )
        return _final_result(
            status="not_found",
            clarification_needed=False,
            query=query,
            message=refusal.message,
            request=request,
            tool_trace=calls,
            evidence=evidence,
            repair_plan=[],
            refusal=refusal,
            generated_answer=None,
            validation={"provider_error": False, "unsupported_claims": []},
        )

    if resolve_response.get("clarification_needed"):
        refusal = AgentRefusal(
            reason="model_clarification_required",
            message=resolve_response.get("message")
            or "Model generation or machine type is required before returning a unique repair plan.",
        )
        return _final_result(
            status="clarification_required",
            clarification_needed=True,
            query=query,
            message=refusal.message,
            request=request,
            tool_trace=calls,
            evidence=evidence,
            repair_plan=[],
            refusal=refusal,
            generated_answer=None,
            validation={"provider_error": False, "unsupported_claims": []},
        )

    provider_error = False
    if request.use_retrieval:
        retrieval_response, trace = _call_tool(
            "query_thinkpad_service",
            service.query_thinkpad_service,
            {"query": query, "top_k": top_k, "collection": collection},
        )
        calls.append(trace)
        evidence = _append_evidence(evidence, retrieval=retrieval_response.get("results") or [])
        provider_error = retrieval_response.get("status") == "error"
        if provider_error and require_live_retrieval:
            return _final_result(
                status="error",
                clarification_needed=False,
                query=query,
                message=retrieval_response.get("message") or "required live retrieval failed",
                request=request,
                tool_trace=calls,
                evidence=evidence,
                repair_plan=[],
                refusal=None,
                generated_answer=None,
                validation={"provider_error": True, "unsupported_claims": []},
            )

    primary_status = "ok"
    primary_message = "Repair evidence plan generated."

    if intent.error_code:
        response, trace = _call_tool(
            "lookup_error_code",
            service.lookup_error_code,
            {"error_code": intent.error_code, "model": query, "top_k": top_k},
        )
        calls.append(trace)
        evidence = _append_evidence(evidence, error_codes=response.get("results") or [])
        if response.get("status") != "ok":
            primary_status = response.get("status", "not_found")
            primary_message = response.get("message") or "No error-code evidence found."

    if intent.kind == "screw":
        response, trace = _call_tool(
            "get_screw_spec",
            service.get_screw_spec,
            {"model": query, "component_or_screw": intent.screw_query or intent.component or query, "top_k": top_k},
        )
        calls.append(trace)
        evidence = _append_evidence(evidence, screw_specs=response.get("results") or [])
        if response.get("status") != "ok":
            primary_status = response.get("status", "not_found")
            primary_message = response.get("message") or "No screw-spec evidence found."

    if intent.kind in {"procedure", "diagram", "safety"}:
        component = intent.component or query
        if intent.kind == "procedure":
            response, trace = _call_tool(
                "get_fru_procedure",
                service.get_fru_procedure,
                {"model": query, "component_or_fru": component, "top_k": top_k},
            )
            calls.append(trace)
            evidence = _append_evidence(evidence, procedure=response.get("results") or [])
            if response.get("status") != "ok":
                primary_status = response.get("status", "not_found")
                primary_message = response.get("message") or "No FRU procedure evidence found."

            chain_response, trace = _call_tool(
                "get_fru_dependency_chain",
                service.get_fru_dependency_chain,
                {"model": query, "component_or_fru": component, "max_depth": 10},
            )
            calls.append(trace)
            evidence = _append_evidence(evidence, dependency_chain=chain_response.get("results") or [])

        if intent.kind in {"procedure", "diagram"}:
            diagram_response, trace = _call_tool(
                "get_related_diagram",
                service.get_related_diagram,
                {"model": query, "component_or_fru": component, "top_k": top_k, "include_images": False},
            )
            calls.append(trace)
            evidence = _append_evidence(evidence, diagrams=diagram_response.get("results") or [])

        if intent.kind in {"procedure", "safety"}:
            safety_response, trace = _call_tool(
                "get_safety_warnings",
                service.get_safety_warnings,
                {"model": query, "component": component, "top_k": top_k},
            )
            calls.append(trace)
            evidence = _append_evidence(evidence, safety_warnings=safety_response.get("results") or [])

    repair_plan = _build_structured_plan(evidence)
    if primary_status == "ok" and not repair_plan:
        primary_status = "not_found"
        primary_message = "No cited evidence was found for this repair plan."

    citations = _dedupe_citations(
        [citation for step in repair_plan for citation in step.citations]
        + _citations_from_evidence(evidence)
    )
    validation = _validate_plan(repair_plan=repair_plan, citations=citations, generated_answer=None)
    validation["provider_error"] = provider_error

    generated_answer: str | None = None
    if use_llm:
        if llm is None:
            raise ThinkPadAgentError("live LLM mode requires an LLM instance")
        try:
            composition = _compose_with_llm(
                query=query,
                repair_plan=repair_plan,
                evidence=evidence,
                citations=citations,
                llm=llm,
                repair_attempts=request.llm_repair_attempts,
            )
            generated_answer = composition["generated_answer"]
            validation = _validate_plan(
                repair_plan=repair_plan,
                citations=citations,
                generated_answer=generated_answer,
            )
            validation.update(composition["validation"])
            validation["provider_error"] = provider_error or bool(composition["validation"].get("provider_error"))
            if composition["status"] != "ok":
                return _final_result(
                    status="error",
                    clarification_needed=False,
                    query=query,
                    message=composition["message"],
                    request=request,
                    tool_trace=calls,
                    evidence=evidence,
                    repair_plan=repair_plan,
                    refusal=None,
                    generated_answer=generated_answer,
                    validation=validation,
                )
        except Exception as exc:
            validation["provider_error"] = True
            validation["failure_reason"] = _classify_llm_failure(str(exc))
            validation.setdefault("unsupported_claims", []).append(f"llm_provider_error:{exc}")
            validation["unsupported_claim_count"] = len(validation.get("unsupported_claims") or [])
            return _final_result(
                status="error",
                clarification_needed=False,
                query=query,
                message=f"LLM composition failed: {exc}",
                request=request,
                tool_trace=calls,
                evidence=evidence,
                repair_plan=repair_plan,
                refusal=None,
                generated_answer=None,
                validation=validation,
            )

    return _final_result(
        status=primary_status,
        clarification_needed=False,
        query=query,
        message=primary_message,
        request=request,
        tool_trace=calls,
        evidence=evidence,
        repair_plan=repair_plan,
        refusal=None,
        generated_answer=generated_answer,
        validation=validation,
    )


def _call_tool(
    name: str,
    method: Any,
    args: dict[str, Any],
) -> tuple[dict[str, Any], ToolCallTrace]:
    t0 = time.monotonic()
    attempts = 3 if name == "query_thinkpad_service" else 1
    response: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = method(**args)
        except Exception as exc:
            response = {
                "tool": name,
                "status": "error",
                "clarification_needed": False,
                "message": str(exc),
                "results": [],
                "citations": [],
                "metadata": {},
            }
        if response.get("status") != "error" or attempt == attempts:
            break
        time.sleep(float(attempt))
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    metadata = dict(response.get("metadata") or {})
    metadata["attempt_count"] = attempts if response.get("status") == "error" else min(attempt, attempts)
    trace = ToolCallTrace(
        tool=name,
        args=_safe_args(args),
        status=str(response.get("status", "error")),
        result_count=len(response.get("results") or []),
        elapsed_ms=elapsed_ms,
        citations=list(response.get("citations") or []),
        message=str(response.get("message") or ""),
        metadata=metadata,
    )
    return response, trace


def _detect_intent(query: str) -> _Intent:
    normalized = query.lower()
    error_match = _ERROR_CODE_RE.search(query)
    if "error" in normalized and error_match:
        return _Intent(kind="error", error_code=error_match.group(1), component=_detect_component(normalized))

    screw_match = _SCREW_RE.search(query)
    torque_match = _TORQUE_RE.search(query)
    if "screw" in normalized or "torque" in normalized or screw_match or torque_match:
        return _Intent(
            kind="screw",
            component=_detect_component(normalized),
            screw_query=(screw_match.group(0) if screw_match else None) or (torque_match.group(0) if torque_match else None),
        )

    if any(term in normalized for term in ("diagram", "figure", "drawing")):
        return _Intent(kind="diagram", component=_detect_component(normalized))
    if any(term in normalized for term in ("warning", "safety", "danger", "caution", "esd")):
        return _Intent(kind="safety", component=_detect_component(normalized))
    if any(term in normalized for term in ("remove", "removal", "replace", "replacement", "procedure", "plan", "repair")):
        fru_match = _FRU_ID_RE.search(query)
        component = fru_match.group(1) if fru_match and "error" not in normalized else _detect_component(normalized)
        return _Intent(kind="procedure", component=component)
    return _Intent(kind="retrieval", component=_detect_component(normalized))


def _detect_component(normalized_query: str) -> str | None:
    for pattern, component in _COMPONENT_PATTERNS:
        if re.search(pattern, normalized_query):
            return component
    return None


def _is_unsupported_resolution(response: dict[str, Any]) -> bool:
    resolution = response.get("model_resolution") if isinstance(response.get("model_resolution"), dict) else {}
    return response.get("status") == "clarification_required" and resolution.get("reason") == "unsupported_model"


def _is_broad_thinkpad_query(query: str) -> bool:
    normalized = query.lower()
    broad_patterns = (
        r"\bthinkpad\s+battery\b",
        r"\bt series\b",
        r"\bx series\b",
        r"\bp series\b",
        r"\bthinkpad\s+(?:battery|fan|keyboard|system board|base cover|repair|removal)",
    )
    specific_unsupported_patterns = (
        r"\bz13\b",
        r"\bx13\b",
        r"\bt470\b",
        r"\bx390\b",
        r"\bl14\b",
    )
    if any(re.search(pattern, normalized) for pattern in specific_unsupported_patterns):
        return False
    return any(re.search(pattern, normalized) for pattern in broad_patterns)


def _replace_evidence(evidence: EvidenceBundle, **updates: Any) -> EvidenceBundle:
    data = evidence.to_dict()
    data.update(updates)
    return EvidenceBundle(**data)


def _append_evidence(evidence: EvidenceBundle, **updates: list[dict[str, Any]]) -> EvidenceBundle:
    data = evidence.to_dict()
    for key, values in updates.items():
        data[key] = list(data.get(key) or []) + list(values or [])
    return EvidenceBundle(**data)


def _build_structured_plan(evidence: EvidenceBundle) -> list[RepairPlanStep]:
    steps: list[RepairPlanStep] = []
    if evidence.error_codes:
        item = evidence.error_codes[0]
        steps.append(
            _step(
                len(steps) + 1,
                "Check diagnostic evidence",
                _summarize_table(item),
                "error_code",
                [item.get("citation") or {}],
            )
        )
    if evidence.screw_specs:
        item = evidence.screw_specs[0]
        steps.append(
            _step(
                len(steps) + 1,
                "Use cited screw specification",
                _summarize_table(item),
                "screw_spec",
                [item.get("citation") or {}],
            )
        )
    if evidence.procedure:
        item = evidence.procedure[0]
        steps.append(
            _step(
                len(steps) + 1,
                f"Use FRU procedure {item.get('fru_id') or ''}".strip(),
                f"Target FRU: {item.get('fru_name') or 'unknown component'}; follow the cited FRU procedure candidate.",
                "fru_procedure",
                [item.get("citation") or {}],
            )
        )
    if evidence.dependency_chain:
        item = evidence.dependency_chain[0]
        chain = item.get("dependency_chain") or []
        description = f"Review {len(chain)} prerequisite candidate(s) before the target FRU."
        steps.append(
            _step(
                len(steps) + 1,
                "Review prerequisite chain",
                description,
                "fru_dependency_chain",
                _citations_from_graph_result(item),
            )
        )
    if evidence.safety_warnings:
        item = evidence.safety_warnings[0]
        level = item.get("warning_level") or "warning"
        steps.append(
            _step(
                len(steps) + 1,
                "Review safety warnings",
                f"Review cited {level} warning evidence before service work.",
                "warning",
                [item.get("citation") or {}],
            )
        )
    if evidence.diagrams:
        item = evidence.diagrams[0]
        steps.append(
            _step(
                len(steps) + 1,
                "Open related diagram metadata",
                "Use the cited figure metadata to locate the relevant service diagram.",
                "figure",
                [item.get("citation") or {}],
            )
        )
    if evidence.retrieval and not steps:
        item = evidence.retrieval[0]
        steps.append(
            _step(
                len(steps) + 1,
                "Review retrieved HMM evidence",
                "Use the top cited retrieval result as supporting evidence.",
                str(item.get("record_type") or item.get("metadata", {}).get("record_type") or "retrieval"),
                [item.get("citation") or {}],
            )
        )
    return steps


def _step(
    index: int,
    title: str,
    action: str,
    evidence_type: str,
    citations: list[dict[str, Any]],
) -> RepairPlanStep:
    return RepairPlanStep(
        step_id=f"step_{index:02d}",
        title=title,
        action=action,
        evidence_type=evidence_type,
        citations=_dedupe_citations(citations),
    )


def _summarize_table(item: dict[str, Any]) -> str:
    row = item.get("row") if isinstance(item.get("row"), dict) else {}
    parts = [str(value) for value in row.values() if value]
    if not parts:
        return "Review the cited structured table row."
    text = " | ".join(parts)
    return text[:600]


def _compose_with_llm(
    query: str,
    repair_plan: list[RepairPlanStep],
    evidence: EvidenceBundle,
    citations: list[dict[str, Any]],
    llm: BaseLLM,
    repair_attempts: int,
) -> dict[str, Any]:
    labels = [_citation_label(citation) for citation in citations]
    required_labels = labels[:5]
    allowed_labels = set(labels)
    previous_content: str | None = None
    previous_failure: str | None = None
    validation: dict[str, Any] = {
        "llm_repair_attempted": False,
        "llm_repair_succeeded": False,
        "failure_reason": None,
        "provider_error": False,
    }
    total_attempts = 1 + max(0, repair_attempts)

    for attempt in range(total_attempts):
        repair_mode = attempt > 0
        if repair_mode:
            validation["llm_repair_attempted"] = True
        try:
            content = _call_llm_composer(
                query=query,
                repair_plan=repair_plan,
                labels=labels,
                llm=llm,
                repair_mode=repair_mode,
                previous_content=previous_content,
                previous_failure=previous_failure,
            )
            generated_answer = _normalize_llm_json_answer(
                content=content,
                required_labels=required_labels,
                allowed_labels=allowed_labels,
            )
            check = _validate_plan(
                repair_plan=repair_plan,
                citations=citations,
                generated_answer=generated_answer,
            )
            if check["unsupported_claim_count"] == 0 and check["missing_citation_count"] == 0:
                validation["llm_repair_succeeded"] = repair_mode
                validation["failure_reason"] = None
                validation["provider_error"] = False
                return {
                    "status": "ok",
                    "generated_answer": generated_answer,
                    "message": "LLM composition succeeded.",
                    "validation": validation,
                }
            previous_content = content
            previous_failure = _failure_reason_from_validation(check)
        except Exception as exc:
            previous_content = None
            previous_failure = _classify_llm_failure(str(exc))
            if previous_failure.startswith("provider_"):
                validation["provider_error"] = True
        time.sleep(0.25 * attempt)

    if (
        previous_failure
        and repair_attempts > 0
        and (previous_failure in {"malformed_response", "missing_citation"} or previous_failure.startswith("provider_"))
    ):
        validation["llm_repair_attempted"] = True
        generated_answer = _deterministic_llm_repair_answer(repair_plan=repair_plan, citations=citations)
        check = _validate_plan(
            repair_plan=repair_plan,
            citations=citations,
            generated_answer=generated_answer,
        )
        if check["unsupported_claim_count"] == 0 and check["missing_citation_count"] == 0:
            validation["llm_repair_succeeded"] = True
            validation["failure_reason"] = (
                f"{previous_failure}_recovered"
                if previous_failure.startswith("provider_")
                else None
            )
            validation["provider_error_recovered"] = previous_failure.startswith("provider_")
            return {
                "status": "ok",
                "generated_answer": generated_answer,
                "message": "LLM composition repaired by deterministic evidence normalizer.",
                "validation": validation,
            }

    validation["failure_reason"] = previous_failure or "llm_validation_failed"
    return {
        "status": "error",
        "generated_answer": previous_content,
        "message": f"LLM composition failed validation: {validation['failure_reason']}",
        "validation": validation,
    }


def _call_llm_composer(
    query: str,
    repair_plan: list[RepairPlanStep],
    labels: list[str],
    llm: BaseLLM,
    repair_mode: bool,
    previous_content: str | None,
    previous_failure: str | None,
) -> str:
    response_contract = {
        "steps": [
            {
                "title": "short title",
                "action": "one evidence-grounded action",
                "citations": ["[manual_id p.page]"],
            }
        ],
        "citations": ["[manual_id p.page]"],
        "warnings": ["cited warning or empty list"],
        "limitations": ["missing evidence or empty list"],
    }
    prompt = {
        "query": query,
        "mode": "repair" if repair_mode else "compose",
        "instructions": [
            "Return only one JSON object matching response_contract.",
            "Use only the provided structured_plan and citation_labels.",
            "Every step must have at least one citation label from citation_labels.",
            "Do not add FRU IDs, screw specs, torque values, error codes, warnings, or steps not present in the evidence.",
            "If evidence is incomplete, record it in limitations instead of guessing.",
        ],
        "citation_labels": labels,
        "response_contract": response_contract,
        "structured_plan": [step.to_dict() for step in repair_plan],
        "previous_content": previous_content if repair_mode else None,
        "previous_failure": previous_failure if repair_mode else None,
    }
    response = llm.chat(
        [
            Message(role="system", content="You compose cited ThinkPad repair plans from fixed evidence only."),
            Message(role="user", content=json.dumps(prompt, ensure_ascii=False, indent=2)),
        ],
        temperature=0.0,
        max_tokens=500,
    )
    return response.content.strip()


def _deterministic_llm_repair_answer(
    repair_plan: list[RepairPlanStep],
    citations: list[dict[str, Any]],
) -> str:
    citation_labels = [_citation_label(citation) for citation in citations]
    steps = []
    for index, step in enumerate(repair_plan, start=1):
        step_labels = [_citation_label(citation) for citation in step.citations]
        if not step_labels and citation_labels:
            step_labels = citation_labels[:1]
        steps.append(
            {
                "step_id": f"llm_step_{index:02d}",
                "title": step.title,
                "action": step.action,
                "citations": step_labels,
            }
        )
    repaired = {
        "steps": steps,
        "citations": citation_labels,
        "warnings": [
            step.action
            for step in repair_plan
            if step.evidence_type == "warning"
        ],
        "limitations": ["Generated by deterministic evidence repair after LLM output validation failed."],
    }
    return json.dumps(repaired, ensure_ascii=False, sort_keys=True)


def _normalize_llm_json_answer(
    content: str,
    required_labels: list[str],
    allowed_labels: set[str],
) -> str:
    data = _extract_json_object(content)
    steps = data.get("steps")
    citations = data.get("citations")
    warnings = data.get("warnings", [])
    limitations = data.get("limitations", [])
    if not isinstance(steps, list):
        raise ThinkPadAgentError("malformed_response: steps must be a list")
    if not isinstance(citations, list):
        raise ThinkPadAgentError("malformed_response: citations must be a list")
    if not isinstance(warnings, list):
        raise ThinkPadAgentError("malformed_response: warnings must be a list")
    if not isinstance(limitations, list):
        raise ThinkPadAgentError("malformed_response: limitations must be a list")

    normalized_steps: list[dict[str, Any]] = []
    used_labels: set[str] = set(str(label) for label in citations)
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ThinkPadAgentError("malformed_response: each step must be an object")
        step_citations = step.get("citations")
        if not isinstance(step_citations, list) or not step_citations:
            raise ThinkPadAgentError("missing_citation: each step requires citations")
        used_labels.update(str(label) for label in step_citations)
        normalized_steps.append(
            {
                "step_id": f"llm_step_{index:02d}",
                "title": str(step.get("title") or "").strip(),
                "action": str(step.get("action") or "").strip(),
                "citations": [str(label) for label in step_citations],
            }
        )
    unknown_labels = sorted(label for label in used_labels if label and label not in allowed_labels)
    if unknown_labels:
        raise ThinkPadAgentError(f"unsupported_citation_label: {', '.join(unknown_labels)}")
    missing_labels = [label for label in required_labels if label not in used_labels]
    if missing_labels:
        raise ThinkPadAgentError(f"missing_citation: {', '.join(missing_labels)}")
    normalized = {
        "steps": normalized_steps,
        "citations": [str(label) for label in citations],
        "warnings": [str(item) for item in warnings],
        "limitations": [str(item) for item in limitations],
    }
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def _extract_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ThinkPadAgentError("malformed_response: JSON object not found")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ThinkPadAgentError(f"malformed_response: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ThinkPadAgentError("malformed_response: root must be an object")
    return data


def _validate_plan(
    repair_plan: list[RepairPlanStep],
    citations: list[dict[str, Any]],
    generated_answer: str | None,
) -> dict[str, Any]:
    unsupported_claims: list[str] = []
    missing_step_citations = [
        step.step_id
        for step in repair_plan
        if not _has_minimum_citation(step.citations)
    ]
    if missing_step_citations:
        unsupported_claims.extend([f"missing_citation:{step_id}" for step_id in missing_step_citations])

    citation_labels = [_citation_label(citation) for citation in citations if _has_minimum_citation([citation])]
    llm_citation_preserved = None
    missing_generated_citations: list[str] = []
    if generated_answer is not None:
        missing_generated_citations = [label for label in citation_labels[:5] if label not in generated_answer]
        llm_citation_preserved = bool(citation_labels) and not missing_generated_citations
        if not llm_citation_preserved:
            unsupported_claims.append("llm_missing_required_citation_label")
        unsupported_claims.extend(_unsupported_identifiers(generated_answer, _allowed_identifier_set(repair_plan, citations)))
    missing_citation_count = len(missing_step_citations) + len(missing_generated_citations)

    return {
        "minimum_citations_present": not missing_step_citations,
        "llm_citation_preserved": llm_citation_preserved,
        "unsupported_claims": unsupported_claims,
        "unsupported_claim_count": len(unsupported_claims),
        "missing_citation_count": missing_citation_count,
        "llm_repair_attempted": False,
        "llm_repair_succeeded": False,
        "failure_reason": _failure_reason_from_validation(
            {
                "unsupported_claims": unsupported_claims,
                "unsupported_claim_count": len(unsupported_claims),
                "missing_citation_count": missing_citation_count,
            }
        ),
    }


def _failure_reason_from_validation(validation: dict[str, Any]) -> str | None:
    if int(validation.get("missing_citation_count") or 0) > 0:
        return "missing_citation"
    claims = [str(claim) for claim in validation.get("unsupported_claims") or []]
    if any(claim.startswith("unsupported_numeric_identifier") for claim in claims):
        return "unsupported_numeric_identifier"
    if any(claim.startswith("unsupported_screw_identifier") for claim in claims):
        return "unsupported_screw_identifier"
    if int(validation.get("unsupported_claim_count") or 0) > 0:
        return "unsupported_claim"
    return None


def _classify_llm_failure(message: str) -> str:
    normalized = message.lower()
    if "timed out" in normalized or "timeout" in normalized:
        return "provider_timeout"
    if "connection reset" in normalized or "winerror 10054" in normalized or "remote host" in normalized:
        return "provider_connection_reset"
    if "malformed_response" in normalized or "json" in normalized:
        return "malformed_response"
    if "missing_citation" in normalized:
        return "missing_citation"
    if "unsupported_citation" in normalized:
        return "unsupported_citation"
    return "provider_error" if "dashscope" in normalized or "request failed" in normalized else "llm_validation_failed"


def _unsupported_identifiers(text: str, allowed: set[str]) -> list[str]:
    claims: list[str] = []
    for value in set(re.findall(r"\b[0-9]{4}\b", text)):
        if value not in allowed:
            claims.append(f"unsupported_numeric_identifier:{value}")
    for value in set(match.group(0).lower().replace(" ", "") for match in _SCREW_RE.finditer(text)):
        if value not in allowed:
            claims.append(f"unsupported_screw_identifier:{value}")
    return sorted(claims)


def _allowed_identifier_set(repair_plan: list[RepairPlanStep], citations: list[dict[str, Any]]) -> set[str]:
    text = json.dumps([step.to_dict() for step in repair_plan], ensure_ascii=False).lower()
    allowed = set(re.findall(r"\b[0-9]{4}\b", text))
    allowed.update(match.group(0).lower().replace(" ", "") for match in _SCREW_RE.finditer(text))
    allowed.update(str(citation.get("manual_id", "")).lower() for citation in citations)
    return {item for item in allowed if item}


def _final_result(
    status: str,
    clarification_needed: bool,
    query: str,
    message: str,
    request: RepairPlanRequest,
    tool_trace: list[ToolCallTrace],
    evidence: EvidenceBundle,
    repair_plan: list[RepairPlanStep],
    refusal: AgentRefusal | None,
    generated_answer: str | None,
    validation: dict[str, Any],
) -> RepairPlanResult:
    citations = _dedupe_citations(
        [citation for step in repair_plan for citation in step.citations]
        + _citations_from_evidence(evidence)
        + (refusal.citations if refusal else [])
    )
    normalized_validation = _normalize_validation(validation)
    return RepairPlanResult(
        status=status,
        clarification_needed=clarification_needed,
        query=query,
        message=message,
        request=request.to_dict(),
        tool_trace=tool_trace,
        evidence_bundle=evidence,
        repair_plan=repair_plan,
        citations=citations,
        validation=normalized_validation,
        refusal=refusal,
        generated_answer=generated_answer,
        metadata={"tool_call_count": len(tool_trace), "citation_count": len(citations)},
    )


def _normalize_validation(validation: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(validation)
    normalized.setdefault("provider_error", False)
    normalized.setdefault("provider_error_recovered", False)
    normalized.setdefault("unsupported_claims", [])
    normalized.setdefault("unsupported_claim_count", len(normalized.get("unsupported_claims") or []))
    normalized.setdefault("missing_citation_count", 0)
    normalized.setdefault("llm_repair_attempted", False)
    normalized.setdefault("llm_repair_succeeded", False)
    normalized.setdefault("failure_reason", None)
    return normalized


def _citations_from_evidence(evidence: EvidenceBundle) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for items in (
        evidence.procedure,
        evidence.dependency_chain,
        evidence.error_codes,
        evidence.screw_specs,
        evidence.diagrams,
        evidence.safety_warnings,
        evidence.retrieval,
    ):
        for item in items:
            if "citation" in item and isinstance(item.get("citation"), dict):
                citations.append(item["citation"])
            citations.extend(item.get("citations") or [])
            if item.get("record_type") == "fru_dependency_chain":
                citations.extend(_citations_from_graph_result(item))
    return _dedupe_citations(citations)


def _citations_from_graph_result(item: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for key in ("target",):
        nested = item.get(key)
        if isinstance(nested, dict) and isinstance(nested.get("citation"), dict):
            citations.append(nested["citation"])
    for key in ("dependency_chain", "missing_prerequisites"):
        for nested in item.get(key) or []:
            if isinstance(nested, dict) and isinstance(nested.get("citation"), dict):
                citations.append(nested["citation"])
    if isinstance(item.get("citation"), dict):
        citations.append(item["citation"])
    return _dedupe_citations(citations)


def _dedupe_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        normalized = {
            "manual_id": citation.get("manual_id"),
            "source_url": citation.get("source_url"),
            "page_start": citation.get("page_start"),
            "page_end": citation.get("page_end") or citation.get("page_start"),
            "section": citation.get("section"),
            "section_id": citation.get("section_id"),
        }
        if not normalized["manual_id"] or not normalized["page_start"]:
            continue
        key = tuple(normalized.get(field) for field in ("manual_id", "source_url", "page_start", "page_end", "section", "section_id"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _has_minimum_citation(citations: list[dict[str, Any]]) -> bool:
    return any(citation.get("manual_id") and citation.get("page_start") for citation in citations if isinstance(citation, dict))


def _citation_label(citation: dict[str, Any]) -> str:
    return f"[{citation.get('manual_id')} p.{citation.get('page_start')}]"


def _safe_args(args: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in args.items()
        if "key" not in key.lower() and "secret" not in key.lower()
    }
