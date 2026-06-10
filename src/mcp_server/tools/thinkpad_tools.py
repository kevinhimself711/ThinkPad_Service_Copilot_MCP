"""ThinkPad-specific MCP tools.

M5 exposes structured ThinkPad HMM evidence as JSON through MCP tools. These
tools intentionally do not generate final repair prose.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from mcp import types

from src.thinkpad.tool_service import ThinkPadToolService, ToolResponse

logger = logging.getLogger(__name__)

LIST_SUPPORTED_MODELS = "list_supported_models"
RESOLVE_THINKPAD_MODEL = "resolve_thinkpad_model"
QUERY_THINKPAD_SERVICE = "query_thinkpad_service"
LOOKUP_ERROR_CODE = "lookup_error_code"
GET_FRU_PROCEDURE = "get_fru_procedure"
GET_SCREW_SPEC = "get_screw_spec"
GET_RELATED_DIAGRAM = "get_related_diagram"
GET_SAFETY_WARNINGS = "get_safety_warnings"


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
    }


TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    LIST_SUPPORTED_MODELS: {
        "description": "List ThinkPad models, generations, machine types, and HMM manuals configured for this service.",
        "input_schema": _schema(
            {
                "include_machine_types": {
                    "type": "boolean",
                    "description": "Include machine type codes in the response.",
                    "default": True,
                }
            }
        ),
    },
    RESOLVE_THINKPAD_MODEL: {
        "description": "Resolve free-form ThinkPad model text to supported model/manual candidates.",
        "input_schema": _schema(
            {
                "query": {
                    "type": "string",
                    "description": "Free-form model text, for example 'X1 Carbon Gen 9' or '21CB'.",
                }
            },
            required=["query"],
        ),
    },
    QUERY_THINKPAD_SERVICE: {
        "description": "Retrieve citation-backed ThinkPad HMM evidence. Returns JSON evidence, not final repair prose.",
        "input_schema": _schema(
            {
                "query": {"type": "string", "description": "ThinkPad HMM service query."},
                "top_k": {
                    "type": "integer",
                    "description": "Maximum evidence records to return.",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                },
                "collection": {
                    "type": "string",
                    "description": "Retrieval collection name.",
                    "default": "thinkpad_m4",
                },
            },
            required=["query"],
        ),
    },
    LOOKUP_ERROR_CODE: {
        "description": "Look up exact ThinkPad HMM error-code table rows with citations.",
        "input_schema": _schema(
            {
                "error_code": {"type": "string", "description": "Error code, for example '0271'."},
                "model": {
                    "type": "string",
                    "description": "Optional model, generation, or machine type filter.",
                },
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            },
            required=["error_code"],
        ),
    },
    GET_FRU_PROCEDURE: {
        "description": "Return structured FRU procedure candidates for an unambiguous ThinkPad model.",
        "input_schema": _schema(
            {
                "model": {"type": "string", "description": "Model/generation or machine type."},
                "component_or_fru": {
                    "type": "string",
                    "description": "Component name or FRU procedure ID.",
                },
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            },
            required=["model", "component_or_fru"],
        ),
    },
    GET_SCREW_SPEC: {
        "description": "Look up structured screw or torque table rows with citations.",
        "input_schema": _schema(
            {
                "model": {"type": "string", "description": "Model/generation or machine type."},
                "component_or_screw": {
                    "type": "string",
                    "description": "Component name, screw size, or torque value.",
                },
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            },
            required=["model", "component_or_screw"],
        ),
    },
    GET_RELATED_DIAGRAM: {
        "description": "Return related figure metadata and citations. M5 does not return image bytes.",
        "input_schema": _schema(
            {
                "model": {"type": "string", "description": "Model/generation or machine type."},
                "component_or_fru": {
                    "type": "string",
                    "description": "Component name or FRU procedure ID.",
                },
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                "include_images": {
                    "type": "boolean",
                    "description": "Request image bytes. M5 always returns metadata only.",
                    "default": False,
                },
            },
            required=["model", "component_or_fru"],
        ),
    },
    GET_SAFETY_WARNINGS: {
        "description": "Return cited safety warnings for a ThinkPad model and optional component.",
        "input_schema": _schema(
            {
                "model": {"type": "string", "description": "Model/generation or machine type."},
                "component": {
                    "type": "string",
                    "description": "Optional component filter, for example 'battery'.",
                },
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            },
            required=["model"],
        ),
    },
}

_tool_service: ThinkPadToolService | None = None


def get_tool_service() -> ThinkPadToolService:
    """Return the module-level service instance."""

    global _tool_service
    if _tool_service is None:
        _tool_service = ThinkPadToolService()
    return _tool_service


def set_tool_service_for_testing(service: ThinkPadToolService | None) -> None:
    """Replace the module service for tests."""

    global _tool_service
    _tool_service = service


async def _call(method: Callable[..., ToolResponse], **kwargs: Any) -> types.CallToolResult:
    try:
        response = await asyncio.to_thread(method, **kwargs)
    except Exception as exc:
        logger.exception("ThinkPad MCP tool failed")
        response = {
            "tool": getattr(method, "__name__", "thinkpad_tool"),
            "status": "error",
            "clarification_needed": False,
            "message": f"internal tool error: {exc}",
            "model_resolution": {},
            "results": [],
            "citations": [],
            "metadata": {},
        }
    return _to_call_tool_result(response)


def _to_call_tool_result(response: ToolResponse) -> types.CallToolResult:
    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True),
            )
        ],
        isError=response.get("status") == "error",
    )


async def list_supported_models_handler(include_machine_types: bool = True) -> types.CallToolResult:
    return await _call(
        get_tool_service().list_supported_models,
        include_machine_types=include_machine_types,
    )


async def resolve_thinkpad_model_handler(query: str) -> types.CallToolResult:
    return await _call(get_tool_service().resolve_thinkpad_model, query=query)


async def query_thinkpad_service_handler(
    query: str,
    top_k: int = 5,
    collection: str = "thinkpad_m4",
) -> types.CallToolResult:
    return await _call(
        get_tool_service().query_thinkpad_service,
        query=query,
        top_k=top_k,
        collection=collection,
    )


async def lookup_error_code_handler(
    error_code: str,
    model: str | None = None,
    top_k: int = 5,
) -> types.CallToolResult:
    return await _call(
        get_tool_service().lookup_error_code,
        error_code=error_code,
        model=model,
        top_k=top_k,
    )


async def get_fru_procedure_handler(
    model: str,
    component_or_fru: str,
    top_k: int = 5,
) -> types.CallToolResult:
    return await _call(
        get_tool_service().get_fru_procedure,
        model=model,
        component_or_fru=component_or_fru,
        top_k=top_k,
    )


async def get_screw_spec_handler(
    model: str,
    component_or_screw: str,
    top_k: int = 5,
) -> types.CallToolResult:
    return await _call(
        get_tool_service().get_screw_spec,
        model=model,
        component_or_screw=component_or_screw,
        top_k=top_k,
    )


async def get_related_diagram_handler(
    model: str,
    component_or_fru: str,
    top_k: int = 5,
    include_images: bool = False,
) -> types.CallToolResult:
    return await _call(
        get_tool_service().get_related_diagram,
        model=model,
        component_or_fru=component_or_fru,
        top_k=top_k,
        include_images=include_images,
    )


async def get_safety_warnings_handler(
    model: str,
    component: str | None = None,
    top_k: int = 5,
) -> types.CallToolResult:
    return await _call(
        get_tool_service().get_safety_warnings,
        model=model,
        component=component,
        top_k=top_k,
    )


HANDLERS: dict[str, Callable[..., Awaitable[types.CallToolResult]]] = {
    LIST_SUPPORTED_MODELS: list_supported_models_handler,
    RESOLVE_THINKPAD_MODEL: resolve_thinkpad_model_handler,
    QUERY_THINKPAD_SERVICE: query_thinkpad_service_handler,
    LOOKUP_ERROR_CODE: lookup_error_code_handler,
    GET_FRU_PROCEDURE: get_fru_procedure_handler,
    GET_SCREW_SPEC: get_screw_spec_handler,
    GET_RELATED_DIAGRAM: get_related_diagram_handler,
    GET_SAFETY_WARNINGS: get_safety_warnings_handler,
}


def register_tools(protocol_handler: Any) -> None:
    """Register all ThinkPad-specific MCP tools."""

    for name, definition in TOOL_DEFINITIONS.items():
        protocol_handler.register_tool(
            name=name,
            description=definition["description"],
            input_schema=definition["input_schema"],
            handler=HANDLERS[name],
        )
        logger.info("Registered MCP tool: %s", name)
