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
_SELECTION_VERSION = "m8_10_stable_primary_v2"
_PRECISION_COMPONENT_RE = re.compile(
    r"\b("
    r"coin[- ]cell|bracket|pen charger|pen holder|nfc|memory|edp|antenna|hinge|"
    r"keyboard bezel|earbuds|system board|i/o|rj45"
    r")\b",
    re.I,
)

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

    render_jobs = _ordered_render_jobs(procedure, figures_by_id)
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
            should_clip = figure.get("figure_kind") in {"region_crop", "region_crop_precise", "region_crop_anchored"}
            bbox = figure.get("bbox") if should_clip and isinstance(figure.get("bbox"), (list, tuple)) else None
            clip = None
            if bbox and len(bbox) == 4:
                clip = fitz.Rect(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
            pixmap = doc[page_number - 1].get_pixmap(clip=clip)
            images.append(ImageInput(data=pixmap.tobytes("png"), mime_type="image/png"))
    finally:
        doc.close()
    return images


def select_primary_figure(
    procedure: dict[str, Any],
    figures_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Choose the first image sent to qwen-vl without changing evidence payloads."""

    jobs = _related_figures(procedure, figures_by_id)
    if not jobs:
        return None
    has_exact_region = any(_same_fru(procedure, figure) and _is_region_crop(figure) for figure in jobs)
    return max(
        enumerate(jobs),
        key=lambda item: (_figure_score(procedure, item[1], has_exact_region), -item[0]),
    )[1]


def primary_figure_metadata(
    procedure: dict[str, Any],
    figures_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    figure = select_primary_figure(procedure, figures_by_id)
    if figure is None:
        return {}
    related = procedure.get("related_image_ids") or []
    has_exact_region = any(_same_fru(procedure, candidate) and _is_region_crop(candidate) for candidate in _related_figures(procedure, figures_by_id))
    return {
        "primary_image_id": figure.get("image_id"),
        "primary_index": related.index(figure.get("image_id")) if figure.get("image_id") in related else None,
        "primary_figure_kind": figure.get("figure_kind") or "unknown",
        "primary_page": figure.get("page"),
        "primary_bbox": figure.get("bbox"),
        "primary_source_image_id": figure.get("source_image_id"),
        "primary_selection_score": _figure_score(procedure, figure, has_exact_region),
        "primary_selection_reason": _selection_reason(procedure, figure, has_exact_region),
    }


def _ordered_render_jobs(
    procedure: dict[str, Any],
    figures_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    jobs = _related_figures(procedure, figures_by_id)
    primary = select_primary_figure(procedure, figures_by_id)
    if primary is None:
        return jobs
    primary_id = primary.get("image_id")
    return [primary, *[figure for figure in jobs if figure.get("image_id") != primary_id]]


def _related_figures(
    procedure: dict[str, Any],
    figures_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    figures: list[dict[str, Any]] = []
    for image_id in procedure.get("related_image_ids") or []:
        figure = figures_by_id.get(image_id)
        if figure and isinstance(figure.get("page"), int):
            figures.append(figure)
    return figures


def _figure_score(
    procedure: dict[str, Any],
    figure: dict[str, Any],
    _has_exact_region: bool,
) -> int:
    kind = figure.get("figure_kind") or "unknown"
    score = {
        "embedded_image": 90,
        "region_crop_anchored": 84,
        "page_raster": 70,
        "region_crop": 65,
        "region_crop_precise": 55,
        "unknown": 20,
    }.get(kind, 20)
    if _same_fru(procedure, figure):
        score += 20
    if kind == "region_crop_precise":
        score += _crop_tightness_bonus(figure)
    return score


def _selection_reason(
    procedure: dict[str, Any],
    figure: dict[str, Any],
    has_exact_region: bool,
) -> str:
    parts = [figure.get("figure_kind") or "unknown"]
    if _same_fru(procedure, figure):
        parts.append("same_fru")
    if _is_precision_component(procedure):
        parts.append("precision_component")
    if has_exact_region:
        parts.append("has_exact_region")
    return "+".join(parts)


def _same_fru(procedure: dict[str, Any], figure: dict[str, Any]) -> bool:
    return str(figure.get("related_fru_id") or "") == str(procedure.get("fru_id") or "")


def _is_region_crop(figure: dict[str, Any]) -> bool:
    return figure.get("figure_kind") in {"region_crop", "region_crop_precise", "region_crop_anchored"}


def _is_precision_component(procedure: dict[str, Any]) -> bool:
    return bool(_PRECISION_COMPONENT_RE.search(str(procedure.get("fru_name") or "")))


def _crop_tightness_bonus(figure: dict[str, Any]) -> int:
    bbox = figure.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return 0
    width = max(0.0, float(bbox[2]) - float(bbox[0]))
    height = max(0.0, float(bbox[3]) - float(bbox[1]))
    area = width * height
    if area <= 80_000:
        return 10
    if area <= 160_000:
        return 5
    return 0


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
    return f"{_SELECTION_VERSION}|{procedure.get('procedure_id')}|{','.join(related)}"


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
