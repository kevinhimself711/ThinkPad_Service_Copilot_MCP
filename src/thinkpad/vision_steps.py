"""Vision-derived removal steps for image_only FRU procedures (M8.7).

Most ThinkPad HMM removal procedures are exploded-view figures with no textual
steps. M8.6 returns the authoritative diagram + screw/torque table for these. M8.7
ADDITIVELY reconstructs textual *action descriptions* from the diagram using a
vision LLM (qwen-vl). These are marked UNVERIFIED and must never carry torque,
screw counts, FRU IDs, or model identity (AGENTS.md 6.4 / 18): the figure and the
structured tables remain the authoritative sources. Results are cached to a
gitignored JSONL so the online per-query call happens at most once per procedure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.libs.llm.base_vision_llm import BaseVisionLLM, ImageInput

VISION_STEP_KIND = "vision_removal_step"
VISION_CITATION_SOURCE = "qwen_vl_unverified"
_MAX_VISION_STEPS = 12
_DEFAULT_CACHE_PATH = Path("data/extracted/m3/vision_steps.jsonl")

# Reject any reconstructed step that leaks an exact spec the LLM must not be the
# source of truth for (torque / screw counts / FRU IDs). AGENTS.md 18.
_SPEC_LEAK_RE = re.compile(
    r"\b\d+(\.\d+)?\s*(nm|kgf|mm)\b|\bm2(\.\d)?\s*[x×]\b|\btorque\b|"
    r"\bscrew\s*\(quantity\)|\bfru\s*\d{3,4}\b",
    re.I,
)

_VISION_PROMPT = (
    "You are reading an exploded-view service diagram for removing a laptop "
    "component. Describe ONLY the physical removal motions a technician performs, "
    "in order, as short imperative steps (e.g. 'Disconnect the cable', 'Lift the "
    "bracket'). Rules: do NOT state screw counts, torque values, screw sizes, FRU "
    "part numbers, or model names — those come from the manual's tables, not the "
    "image. If the diagram is unclear, return fewer steps. Output one step per "
    "line, numbered."
)


def render_procedure_images(
    procedure: dict[str, Any],
    figures_by_id: dict[str, dict[str, Any]],
    pdf_path: str | Path,
) -> list[ImageInput]:
    """Render the pages of a procedure's attributed figures to PNG bytes.

    Renders in-memory (no disk write) to avoid materializing copyrighted image
    files. Region-crop figures carry a page-coordinate bbox; those are rendered
    with a PyMuPDF clip so qwen-vl sees the intended sub-page diagram instead
    of the whole shared FRU page.
    """

    related = procedure.get("related_image_ids") or []
    render_jobs: list[dict[str, Any]] = []
    for image_id in related:
        figure = figures_by_id.get(image_id)
        if figure and isinstance(figure.get("page"), int):
            render_jobs.append(figure)
    if not render_jobs:
        return []

    try:
        import fitz  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("PyMuPDF is required to render procedure diagrams") from exc

    images: list[ImageInput] = []
    doc = fitz.open(str(pdf_path))
    try:
        for figure in render_jobs:
            page_number = int(figure["page"])
            if page_number < 1 or page_number > doc.page_count:
                continue
            should_clip = figure.get("figure_kind") == "region_crop"
            bbox = figure.get("bbox") if should_clip and isinstance(figure.get("bbox"), (list, tuple)) else None
            clip = None
            if bbox and len(bbox) == 4:
                clip = fitz.Rect(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
            pixmap = doc[page_number - 1].get_pixmap(clip=clip)
            images.append(ImageInput(data=pixmap.tobytes("png"), mime_type="image/png"))
    finally:
        doc.close()
    return images


def _parse_step_lines(content: str) -> list[str]:
    """Parse a vision response into ordered step texts, defensively.

    Accepts numbered lines ("1. ...") or plain lines; drops blanks, headers, and
    anything that leaks an exact spec the LLM must not author.
    """

    steps: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", line).strip()
        if len(line) < 4:
            continue
        if _SPEC_LEAK_RE.search(line):
            continue
        steps.append(line)
        if len(steps) >= _MAX_VISION_STEPS:
            break
    return steps


def reconstruct_steps(
    vision_llm: BaseVisionLLM,
    images: list[ImageInput],
    procedure: dict[str, Any],
) -> list[dict[str, Any]]:
    """Call the vision LLM on the diagram images and return unverified steps.

    Returns [] on no images, empty output, or any failure — the caller then
    degrades to the M8.6 figure-only behavior.
    """

    if not images:
        return []
    fru_name = procedure.get("fru_name") or "component"
    prompt = f"{_VISION_PROMPT}\nComponent being removed: {fru_name}."
    try:
        # Send the first diagram page; additional pages are rare and the first
        # exploded view is the primary removal illustration.
        response = vision_llm.chat_with_image(prompt, images[0])
    except Exception:  # noqa: BLE001 - vision output is untrusted; degrade quietly
        return []

    content = getattr(response, "content", "") or ""
    texts = _parse_step_lines(content)
    citation = procedure.get("citation") or {}
    steps: list[dict[str, Any]] = []
    for index, text in enumerate(texts, start=1):
        steps.append(
            {
                "step_index": index,
                "text": text,
                "step_kind": VISION_STEP_KIND,
                "citation_source": VISION_CITATION_SOURCE,
                "verified": False,
                "provenance": "qwen-vl",
                "citation": citation,
            }
        )
    return steps


def _cache_key(procedure: dict[str, Any]) -> str:
    related = sorted(str(i) for i in (procedure.get("related_image_ids") or []))
    return f"{procedure.get('procedure_id')}|{','.join(related)}"


def load_cache(cache_path: str | Path = _DEFAULT_CACHE_PATH) -> dict[str, list[dict[str, Any]]]:
    path = Path(cache_path)
    if not path.exists():
        return {}
    cache: dict[str, list[dict[str, Any]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = row.get("key")
        if key is not None:
            cache[key] = row.get("steps") or []
    return cache


def get_or_reconstruct(
    vision_llm: BaseVisionLLM,
    procedure: dict[str, Any],
    figures_by_id: dict[str, dict[str, Any]],
    pdf_path: str | Path,
    cache: dict[str, list[dict[str, Any]]] | None = None,
    cache_path: str | Path = _DEFAULT_CACHE_PATH,
) -> list[dict[str, Any]]:
    """Return cached vision steps for a procedure, or reconstruct and cache them.

    The online vision call happens at most once per (procedure, images) key; all
    later queries hit the gitignored JSONL cache.
    """

    key = _cache_key(procedure)
    if cache is not None and key in cache:
        return cache[key]

    images = render_procedure_images(procedure, figures_by_id, pdf_path)
    steps = reconstruct_steps(vision_llm, images, procedure)

    if cache is not None:
        cache[key] = steps
    _append_cache(cache_path, key, steps)
    return steps


def _append_cache(cache_path: str | Path, key: str, steps: list[dict[str, Any]]) -> None:
    path = Path(cache_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"key": key, "steps": steps}, ensure_ascii=False) + "\n")
    except OSError:  # pragma: no cover - cache write is best-effort
        pass
