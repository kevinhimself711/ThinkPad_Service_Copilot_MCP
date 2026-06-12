"""In-memory FRU dependency graph for ThinkPad HMM procedure records."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class FRUDependencyGraph:
    """Directed prerequisite graph keyed by manual ID and FRU ID."""

    def __init__(
        self,
        procedures: list[dict[str, Any]],
        dependency_edges: list[dict[str, Any]],
        manual_ids: set[str] | None = None,
    ) -> None:
        allowed = {manual_id.lower() for manual_id in manual_ids or set()}
        self._procedures: dict[tuple[str, str], dict[str, Any]] = {}
        self._edges: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for procedure in procedures:
            manual_id = str(procedure.get("manual_id") or "")
            fru_id = str(procedure.get("fru_id") or "")
            if not manual_id or not fru_id:
                continue
            if allowed and manual_id.lower() not in allowed:
                continue
            self._procedures[(manual_id, fru_id)] = dict(procedure)

        for edge in dependency_edges:
            manual_id = str(edge.get("manual_id") or "")
            source_fru_id = str(edge.get("source_fru_id") or "")
            required_fru_id = str(edge.get("required_fru_id") or "")
            if not manual_id or not source_fru_id or not required_fru_id:
                continue
            if allowed and manual_id.lower() not in allowed:
                continue
            self._edges[(manual_id, source_fru_id)].append(dict(edge))

        for key, edges in self._edges.items():
            self._edges[key] = sorted(
                edges,
                key=lambda item: (
                    str(item.get("required_fru_id") or ""),
                    _citation_page(item),
                ),
            )

    def get_dependency_chain(
        self,
        manual_id: str,
        fru_id: str,
        max_depth: int = 10,
    ) -> dict[str, Any]:
        """Return recursive prerequisite evidence for a FRU procedure."""

        if max_depth < 1:
            raise ValueError("max_depth must be >= 1")

        key = (manual_id, fru_id)
        target = self._procedures.get(key)
        if target is None:
            return {
                "manual_id": manual_id,
                "target": {"manual_id": manual_id, "fru_id": fru_id},
                "dependency_chain": [],
                "edge_count": 0,
                "missing_prerequisites": [],
                "cycle_detected": False,
                "cycles": [],
                "truncated": False,
                "max_depth": max_depth,
                "found": False,
            }

        chain: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        cycles: list[dict[str, Any]] = []
        seen_nodes: set[tuple[str, str]] = set()
        traversed_edges: set[tuple[str, str, str]] = set()
        truncated = False

        def visit(current_key: tuple[str, str], depth: int, path: list[str]) -> None:
            nonlocal truncated
            if depth >= max_depth:
                if self._edges.get(current_key):
                    truncated = True
                return

            for edge in self._edges.get(current_key, []):
                required_id = str(edge.get("required_fru_id") or "")
                required_key = (current_key[0], required_id)
                traversed_edges.add((current_key[0], current_key[1], required_id))
                edge_path = [*path, required_id]

                if required_id in path:
                    cycles.append(
                        {
                            "manual_id": current_key[0],
                            "path": edge_path,
                            "citation": _citation_for(edge),
                        }
                    )
                    continue

                required = self._procedures.get(required_key)
                if required is None:
                    missing.append(
                        {
                            "manual_id": current_key[0],
                            "fru_id": required_id,
                            "required_by": current_key[1],
                            "depth": depth + 1,
                            "edge_path": edge_path,
                            "citation": _citation_for(edge),
                        }
                    )
                    continue

                if required_key not in seen_nodes:
                    seen_nodes.add(required_key)
                    chain.append(_node_evidence(required, depth=depth + 1, edge_path=edge_path))
                visit(required_key, depth + 1, edge_path)

        visit(key, 0, [fru_id])

        return {
            "manual_id": manual_id,
            "target": _node_evidence(target, depth=0, edge_path=[fru_id]),
            "dependency_chain": chain,
            "edge_count": len(traversed_edges),
            "missing_prerequisites": missing,
            "cycle_detected": bool(cycles),
            "cycles": cycles,
            "truncated": truncated,
            "max_depth": max_depth,
            "found": True,
        }


def build_fru_dependency_graph(
    procedures: list[dict[str, Any]],
    dependency_edges: list[dict[str, Any]],
    manual_ids: set[str] | None = None,
) -> FRUDependencyGraph:
    """Build an in-memory FRU dependency graph from M3 JSONL-like records."""

    return FRUDependencyGraph(
        procedures=procedures,
        dependency_edges=dependency_edges,
        manual_ids=manual_ids,
    )


def _node_evidence(record: dict[str, Any], depth: int, edge_path: list[str]) -> dict[str, Any]:
    return {
        "manual_id": record.get("manual_id"),
        "fru_id": record.get("fru_id"),
        "fru_name": record.get("fru_name"),
        "procedure_id": record.get("procedure_id"),
        "depth": depth,
        "edge_path": edge_path,
        "warnings": record.get("warnings") or [],
        "citation": _citation_for(record),
    }


def _citation_for(record: dict[str, Any]) -> dict[str, Any]:
    citation = record.get("citation") if isinstance(record.get("citation"), dict) else {}
    page_start = citation.get("page_start") or record.get("page_start") or record.get("page")
    page_end = citation.get("page_end") or record.get("page_end") or page_start
    return {
        "manual_id": citation.get("manual_id") or record.get("manual_id"),
        "source_url": citation.get("source_url") or record.get("source_url"),
        "page_start": page_start,
        "page_end": page_end,
        "section": citation.get("section"),
        "section_id": citation.get("section_id") or record.get("fru_id"),
    }


def _citation_page(record: dict[str, Any]) -> int:
    citation = record.get("citation") if isinstance(record.get("citation"), dict) else {}
    page = citation.get("page_start") or record.get("page_start") or record.get("page") or 0
    try:
        return int(page)
    except (TypeError, ValueError):
        return 0
