"""FRU procedure and prerequisite extraction for ThinkPad HMM pages."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from src.thinkpad.manifest import ManualMetadata
from src.thinkpad.models import (
    Citation,
    DependencyEdge,
    FigureRecord,
    FRUProcedure,
    FRUStepRecord,
    HMMPage,
)

_FRU_HEADING_RE = re.compile(r"(?m)^\s*(?P<fru_id>\d{4})\s+(?P<name>[A-Za-z][^\n]{2,120})$")
_FRU_REF_RE = re.compile(r"\b(?P<fru_id>[1-9]\d{3})\s+(?P<name>[A-Za-z][A-Za-z0-9 .()&+-]{2,100})")
_PROCEDURE_MARKERS = (
    "removal steps",
    "before removing",
    "before you remove",
    "remove the following",
    "for access, remove",
    "when installing",
)


@dataclass(frozen=True)
class _Section:
    fru_id: str
    fru_name: str
    page_start: int
    page_end: int
    text: str
    raw_text: str
    start_offset: int
    page_offsets: list[tuple[int, int]]
    has_figure: bool = False
    variant_label: str = ""


# A page is treated as carrying a removal figure when it has either embedded
# raster images or a dense vector line drawing. ThinkPad HMMs use both: most
# manuals draw exploded views as vector art (high drawing_count), while a few
# (e.g. T14 Gen 3) embed raster images. A small vector count is just rules and
# table borders, so require a threshold for the vector signal.
_VECTOR_FIGURE_THRESHOLD = 40


def _page_has_figure(page: HMMPage) -> bool:
    if page.embedded_image_count > 0:
        return True
    return page.drawing_count >= _VECTOR_FIGURE_THRESHOLD


# A variant sub-header marks one of several model/type-specific removal
# procedures under a single FRU heading, e.g. "Removal steps of the thermal fan
# assembly (for Intel models)" / "(for AMD models)" / "(type C)". Splitting on
# these keeps Intel vs AMD steps, figures, and pages from being merged.
_VARIANT_HEADER_RE = re.compile(
    r"(?im)^[^\n]*removal steps of[^\n]*\((?:for [^)\n]+|type [a-z])\)[^\n]*$"
)
_VARIANT_LABEL_RE = re.compile(r"\((?:for ([^)\n]+)|type ([a-z]))\)", re.I)


def _split_variant_sections(
    section: _Section, figure_pages: set[int] | None = None
) -> list[_Section]:
    """Split a FRU section into per-variant sub-sections when it contains
    multiple model/type-specific removal sub-procedures. Returns [section]
    unchanged when fewer than two variant headers are present.
    """

    matches = list(_VARIANT_HEADER_RE.finditer(section.raw_text))
    if len(matches) < 2:
        return [section]

    preamble = section.raw_text[: matches[0].start()]
    variants: list[_Section] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section.raw_text)
        body = preamble + section.raw_text[start:end]
        label_match = _VARIANT_LABEL_RE.search(match.group(0))
        raw_label = ""
        if label_match:
            raw_label = (label_match.group(1) or ("type " + label_match.group(2))).strip()
        label = re.sub(r"[^a-z0-9]+", "_", raw_label.lower()).strip("_")
        abs_start = section.start_offset + start
        page_start = _page_for_offset(abs_start, section.page_offsets)
        page_end = _page_for_offset(
            section.start_offset + max(start, end - 1), section.page_offsets
        )
        if figure_pages is None:
            has_figure = section.has_figure
        else:
            has_figure = any(page in figure_pages for page in range(page_start, page_end + 1))
        variants.append(
            _Section(
                fru_id=section.fru_id,
                fru_name=section.fru_name,
                page_start=page_start,
                page_end=page_end,
                text=body.strip(),
                raw_text=body,
                start_offset=abs_start,
                page_offsets=section.page_offsets,
                has_figure=has_figure,
                variant_label=label,
            )
        )
    return variants


def extract_fru_procedures(
    manual: ManualMetadata,
    pages: list[HMMPage],
) -> tuple[list[FRUProcedure], list[DependencyEdge]]:
    """Extract FRU procedure records and prerequisite dependency edges."""

    sections = _find_sections(pages)
    procedures: list[FRUProcedure] = []
    edges: list[DependencyEdge] = []

    for section in sections:
        prerequisites = extract_prerequisites(section.text)
        citation = Citation(
            manual_id=manual.manual_id,
            source_url=manual.source_url,
            page_start=section.page_start,
            page_end=section.page_end,
            section=f"{section.fru_id} {section.fru_name}",
            section_id=section.fru_id,
        )
        step_records = _extract_step_records(manual, section)
        procedure_id = f"{manual.manual_id}_fru_{section.fru_id}"
        if section.variant_label:
            procedure_id = f"{procedure_id}_{section.variant_label}"
        procedures.append(
            FRUProcedure(
                procedure_id=procedure_id,
                manual_id=manual.manual_id,
                fru_id=section.fru_id,
                fru_name=section.fru_name,
                citation=citation,
                steps=_extract_steps(section),
                step_records=step_records,
                prerequisites=prerequisites,
                page_start=section.page_start,
                page_end=section.page_end,
                presentation_type=_classify_presentation(section, step_records),
            )
        )

        for prerequisite in prerequisites:
            required_fru_id = prerequisite.split(" ", 1)[0]
            edges.append(
                DependencyEdge(
                    manual_id=manual.manual_id,
                    source_fru_id=section.fru_id,
                    required_fru_id=required_fru_id,
                    citation=citation,
                )
            )

    return procedures, edges


def attribute_figures_to_procedures(
    figures: list[FigureRecord],
    procedures: list[FRUProcedure],
    pages: list[HMMPage] | None = None,
) -> tuple[list[FigureRecord], list[FRUProcedure]]:
    """Link figures to the FRU procedure that owns them, using within-page
    heading bands when page positional data is available (M8.8).

    A whole-page raster (vector line-art page) is attributed to the FRU whose
    heading band covers the bulk of the page's drawing content; an embedded
    image is attributed by which heading band its bbox falls in. Pages with no
    heading continue the FRU whose heading most recently precedes the page (a
    multi-page diagram). When `pages` is omitted (or carries no positional data),
    falls back to page-span containment with a narrowest-span tiebreak.
    """

    spans = [
        (proc, proc.page_start, proc.page_end)
        for proc in procedures
        if proc.page_start is not None and proc.page_end is not None
    ]
    page_info = {page.page: page for page in (pages or [])}
    # fru_id -> procedures with that fru_id, for mapping a resolved heading to a
    # concrete procedure (variants share a fru_id).
    procs_by_fru: dict[str, list[FRUProcedure]] = {}
    for proc in procedures:
        procs_by_fru.setdefault(proc.fru_id, []).append(proc)
    ordered_starts = sorted(
        ((proc.page_start, proc) for proc in procedures if proc.page_start is not None),
        key=lambda item: item[0],
    )

    region_figures = _build_region_crop_figures(figures, procedures, page_info, procs_by_fru, ordered_starts)
    all_figures = [*figures, *region_figures]

    images_by_proc_id: dict[str, list[str]] = {}
    updated_figures: list[FigureRecord] = []
    for figure in all_figures:
        owner = _resolve_owner(figure, spans, page_info, procs_by_fru, ordered_starts)
        if owner is None:
            updated_figures.append(figure)
            continue
        images_by_proc_id.setdefault(owner.procedure_id, []).append(figure.image_id)
        updated_figures.append(
            replace(
                figure,
                related_fru_id=owner.fru_id,
                related_component=owner.fru_name,
            )
        )

    figure_by_id = {figure.image_id: figure for figure in updated_figures}
    updated_procedures = [
        replace(
            proc,
            related_image_ids=_prioritize_related_images(
                images_by_proc_id.get(proc.procedure_id, list(proc.related_image_ids)),
                figure_by_id,
            ),
        )
        if proc.procedure_id in images_by_proc_id
        else proc
        for proc in procedures
    ]
    return updated_figures, updated_procedures


def _prioritize_related_images(
    image_ids: list[str],
    figure_by_id: dict[str, FigureRecord],
) -> list[str]:
    """Keep stable native figure evidence before experimental crop evidence.

    M8.9 region crops recover some no-image/shared-page cases, but full live
    testing showed that making crops the first image can regress qwen-vl naming
    on procedures whose original page/embedded figure was already correct.
    """

    priority = {
        "embedded_image": 0,
        "page_raster": 1,
        "region_crop": 2,
        "region_crop_precise": 3,
        "unknown": 4,
    }
    return sorted(
        dict.fromkeys(image_ids),
        key=lambda image_id: (
            priority.get((figure_by_id.get(image_id).figure_kind if figure_by_id.get(image_id) else "unknown"), 3),
            image_id,
        ),
    )


def _build_region_crop_figures(
    figures: list[FigureRecord],
    procedures: list[FRUProcedure],
    page_info: dict[int, HMMPage],
    procs_by_fru: dict[str, list[FRUProcedure]],
    ordered_starts: list[tuple[int, FRUProcedure]],
) -> list[FigureRecord]:
    """Create FRU-owned sub-page crop records for shared vector/raster pages.

    The crop records are metadata only; rendering clips the source PDF page later
    in `vision_steps.render_procedure_images`. We only create regions when the
    page has positional signals and vector drawing bands, which avoids replacing
    robust embedded-image extraction with guessed crops.
    """

    by_page: dict[int, FigureRecord] = {}
    for figure in figures:
        if (figure.figure_kind or "unknown") == "page_raster" or figure.image_id.endswith("_raster"):
            by_page.setdefault(figure.page, figure)

    regions: list[FigureRecord] = []
    for page_number, page in page_info.items():
        source = by_page.get(page_number)
        if source is None or not page.fru_headings or not page.drawing_bands:
            continue
        if len(page.fru_headings) < 2 and not _has_above_first_heading_drawing(page):
            continue
        wide_bboxes = dict(_region_bboxes_for_page(page, ordered_starts))
        precise_bboxes = dict(_precise_region_bboxes_for_page(page, ordered_starts))
        for fru_id, bbox in wide_bboxes.items():
            owner = _procedure_for_fru(fru_id, page_number, procs_by_fru)
            if owner is None:
                continue
            if _is_diagnostic_pseudo_fru(owner):
                continue
            region_id = f"{source.image_id}_region_{fru_id}"
            regions.append(
                replace(
                    source,
                    image_id=region_id,
                    caption=f"Region crop for FRU {fru_id} removal diagram",
                    related_fru_id=owner.fru_id,
                    related_component=owner.fru_name,
                    bbox=bbox,
                    figure_kind="region_crop",
                    source_image_id=source.image_id,
                    storage_uri=None,
                )
            )
        for fru_id, bbox in precise_bboxes.items():
            owner = _procedure_for_fru(fru_id, page_number, procs_by_fru)
            if owner is None:
                continue
            if _is_diagnostic_pseudo_fru(owner):
                continue
            if wide_bboxes.get(fru_id) == bbox:
                continue
            region_id = f"{source.image_id}_region_precise_{fru_id}"
            regions.append(
                replace(
                    source,
                    image_id=region_id,
                    caption=f"Precise region crop for FRU {fru_id} removal diagram",
                    related_fru_id=owner.fru_id,
                    related_component=owner.fru_name,
                    bbox=bbox,
                    figure_kind="region_crop_precise",
                    source_image_id=source.image_id,
                    storage_uri=None,
                )
            )
        regions.extend(
            _anchored_region_crops(page, page_number, source, procs_by_fru)
        )
    return regions


def _anchored_region_crops(
    page: HMMPage,
    page_number: int,
    source: FigureRecord,
    procs_by_fru: dict[str, list[FRUProcedure]],
) -> list[FigureRecord]:
    """Emit `region_crop_anchored` figures: crop bands keyed by a removal anchor
    and attributed to the FRU whose name the anchor's component matches (M8.11)."""

    crops: list[FigureRecord] = []
    for component, bbox in _anchored_region_bboxes_for_page(page):
        owner = _owner_for_anchor_component(component, page_number, procs_by_fru)
        if owner is None or _is_diagnostic_pseudo_fru(owner):
            continue
        region_id = f"{source.image_id}_region_anchored_{owner.fru_id}"
        if any(existing.image_id == region_id for existing in crops):
            continue
        crops.append(
            replace(
                source,
                image_id=region_id,
                caption=f"Anchored region crop for FRU {owner.fru_id} removal diagram",
                related_fru_id=owner.fru_id,
                related_component=owner.fru_name,
                bbox=bbox,
                figure_kind="region_crop_anchored",
                source_image_id=source.image_id,
                storage_uri=None,
            )
        )
    return crops


def _owner_for_anchor_component(
    component: str,
    page_number: int,
    procs_by_fru: dict[str, list[FRUProcedure]],
) -> FRUProcedure | None:
    """Find the FRU procedure whose name matches a removal anchor's component.

    Prefers a procedure whose page span contains the anchor's page; among matches
    picks the narrowest span (variant disambiguation), mirroring `_procedure_for_fru`.
    """

    matches = [
        proc
        for procs in procs_by_fru.values()
        for proc in procs
        if _anchor_matches_fru(component, proc.fru_name)
    ]
    if not matches:
        return None
    containing = [
        proc
        for proc in matches
        if proc.page_start is not None
        and proc.page_end is not None
        and proc.page_start <= page_number <= proc.page_end
    ]
    pool = containing or matches
    return min(pool, key=_span_width)


def _is_diagnostic_pseudo_fru(proc: FRUProcedure) -> bool:
    name = proc.fru_name.lower()
    return proc.fru_id.startswith("22") and any(
        marker in name for marker in ("uuid", "invalid", "error", "failure", "configuration")
    )


def _has_above_first_heading_drawing(page: HMMPage) -> bool:
    if not page.fru_headings:
        return False
    first_heading = float(page.fru_headings[0][0])
    return _drawing_overlap(page.drawing_bands, 0.0, first_heading) is not None


def _region_bboxes_for_page(
    page: HMMPage,
    ordered_starts: list[tuple[int, FRUProcedure]],
) -> list[tuple[str, tuple[float, float, float, float]]]:
    if not page.width or not page.height or not page.fru_headings or not page.drawing_bands:
        return []
    regions: dict[str, tuple[float, float]] = {}
    height = float(page.height)
    width = float(page.width)
    headings = page.fru_headings
    boundaries = [float(y) for y, _ in headings] + [height]

    for index, (heading_y, fru_id) in enumerate(headings):
        lo = max(0.0, float(heading_y))
        hi = min(height, boundaries[index + 1])
        overlap = _drawing_overlap(page.drawing_bands, lo, hi)
        if overlap is not None:
            bbox = (0.0, overlap[0], width, overlap[1])
            regions[fru_id] = _merge_bbox(regions.get(fru_id), bbox)

    first_heading = float(headings[0][0])
    above_overlap = _drawing_overlap(page.drawing_bands, 0.0, first_heading)
    if above_overlap is not None:
        preceding = _nearest_preceding(page.page, ordered_starts, exclusive=True)
        if preceding is not None:
            above_bbox = (0.0, above_overlap[0], width, above_overlap[1])
            regions[preceding.fru_id] = _merge_bbox(regions.get(preceding.fru_id), above_bbox)

    return [
        (fru_id, _padded_bbox(bbox[0], bbox[1], bbox[2], bbox[3], width, height))
        for fru_id, bbox in regions.items()
    ]


def _precise_region_bboxes_for_page(
    page: HMMPage,
    ordered_starts: list[tuple[int, FRUProcedure]],
) -> list[tuple[str, tuple[float, float, float, float]]]:
    if not page.width or not page.height or not page.fru_headings or not page.drawing_bands:
        return []
    if not page.drawing_rects:
        return []
    regions: dict[str, tuple[float, float, float, float]] = {}
    height = float(page.height)
    width = float(page.width)
    headings = page.fru_headings
    boundaries = [float(y) for y, _ in headings] + [height]

    for index, (heading_y, fru_id) in enumerate(headings):
        lo = max(0.0, float(heading_y))
        hi = min(height, boundaries[index + 1])
        bbox = _drawing_bbox_overlap(page, lo, hi)
        if bbox is not None:
            regions[fru_id] = _merge_bbox(regions.get(fru_id), bbox)

    first_heading = float(headings[0][0])
    above_bbox = _drawing_bbox_overlap(page, 0.0, first_heading)
    if above_bbox is not None:
        preceding = _nearest_preceding(page.page, ordered_starts, exclusive=True)
        if preceding is not None:
            regions[preceding.fru_id] = _merge_bbox(regions.get(preceding.fru_id), above_bbox)

    return [
        (fru_id, _padded_bbox(bbox[0], bbox[1], bbox[2], bbox[3], width, height))
        for fru_id, bbox in regions.items()
    ]


def _drawing_bbox_overlap(
    page: HMMPage,
    lo: float,
    hi: float,
) -> tuple[float, float, float, float] | None:
    rects = _drawing_rects_in_band(page, lo, hi)
    if rects:
        return _merge_rects(_connected_drawing_cluster(rects))
    overlap = _drawing_overlap(page.drawing_bands, lo, hi)
    if overlap is None or not page.width:
        return None
    return (0.0, overlap[0], float(page.width), overlap[1])


def _drawing_rects_in_band(
    page: HMMPage,
    lo: float,
    hi: float,
    min_size: float = 2.0,
) -> list[tuple[float, float, float, float]]:
    rects: list[tuple[float, float, float, float]] = []
    page_width = float(page.width or 0.0)
    page_height = float(page.height or 0.0)
    for rx0, ry0, rx1, ry1 in page.drawing_rects:
        width = float(rx1) - float(rx0)
        height = float(ry1) - float(ry0)
        if width < min_size or height < min_size:
            continue
        if page_width and width > page_width * 0.92 and height < 6.0:
            continue
        if page_height and height > page_height * 0.92 and width < 6.0:
            continue
        start = max(float(ry0), lo)
        end = min(float(ry1), hi)
        if end - start >= min_size:
            rects.append((float(rx0), start, float(rx1), end))
    return rects


def _connected_drawing_cluster(
    rects: list[tuple[float, float, float, float]],
    gap: float = 18.0,
) -> list[tuple[float, float, float, float]]:
    """Return the largest connected drawing cluster inside a FRU band.

    The goal is not perfect image segmentation; it is to avoid M8.9's full-width
    vertical bands when a page contains several separate line-art regions.
    """

    clusters: list[list[tuple[float, float, float, float]]] = []
    for rect in sorted(rects, key=lambda item: (item[1], item[0])):
        merged = False
        for cluster in clusters:
            if any(_rects_near(rect, other, gap) for other in cluster):
                cluster.append(rect)
                merged = True
                break
        if not merged:
            clusters.append([rect])

    changed = True
    while changed:
        changed = False
        for i in range(len(clusters)):
            if changed:
                break
            for j in range(i + 1, len(clusters)):
                if any(_rects_near(a, b, gap) for a in clusters[i] for b in clusters[j]):
                    clusters[i].extend(clusters.pop(j))
                    changed = True
                    break

    return max(clusters, key=lambda cluster: _rect_area(_merge_rects(cluster))) if clusters else rects


def _rects_near(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    gap: float,
) -> bool:
    return not (
        a[2] + gap < b[0]
        or b[2] + gap < a[0]
        or a[3] + gap < b[1]
        or b[3] + gap < a[1]
    )


def _merge_rects(rects: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    return (
        min(rect[0] for rect in rects),
        min(rect[1] for rect in rects),
        max(rect[2] for rect in rects),
        max(rect[3] for rect in rects),
    )


def _rect_area(rect: tuple[float, float, float, float]) -> float:
    return max(0.0, rect[2] - rect[0]) * max(0.0, rect[3] - rect[1])


def _drawing_overlap(
    drawing_bands: list[tuple[float, float]],
    lo: float,
    hi: float,
    min_height: float = 8.0,
) -> tuple[float, float] | None:
    overlaps: list[tuple[float, float]] = []
    for by0, by1 in drawing_bands:
        start = max(float(by0), lo)
        end = min(float(by1), hi)
        if end - start >= min_height:
            overlaps.append((start, end))
    if not overlaps:
        return None
    return min(start for start, _ in overlaps), max(end for _, end in overlaps)


def _merge_band(
    existing: tuple[float, float] | None,
    new_band: tuple[float, float],
) -> tuple[float, float]:
    if existing is None:
        return new_band
    return min(existing[0], new_band[0]), max(existing[1], new_band[1])


def _merge_bbox(
    existing: tuple[float, float, float, float] | None,
    new_bbox: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    if existing is None:
        return new_bbox
    return (
        min(existing[0], new_bbox[0]),
        min(existing[1], new_bbox[1]),
        max(existing[2], new_bbox[2]),
        max(existing[3], new_bbox[3]),
    )


def _padded_bbox(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    page_width: float,
    page_height: float,
    padding: float = 12.0,
) -> tuple[float, float, float, float]:
    return (
        max(0.0, x0),
        max(0.0, y0 - padding),
        min(page_width, x1),
        min(page_height, y1 + padding),
    )


_ANCHOR_STOPWORDS = frozenset(
    {"the", "a", "an", "and", "of", "with", "for", "assembly", "module", "selected",
     "models", "only", "gen", "its"}
)


def _component_tokens(name: str) -> frozenset[str]:
    """Content tokens of a component/FRU name for anchor<->FRU matching.

    Drops parentheticals, "Gen N", and generic nouns so that "coin-cell battery"
    matches the FRU "Coin-cell battery" but is not swamped by words like
    "assembly" that nearly every FRU name carries.
    """

    lowered = re.sub(r"\(.*?\)", " ", name.lower())
    lowered = re.sub(r"\bgen\s*\d+\b", " ", lowered)
    lowered = lowered.replace("/", " ")
    return frozenset(
        token
        for token in re.findall(r"[a-z0-9.]+", lowered)
        if token not in _ANCHOR_STOPWORDS and len(token) > 1
    )


def _anchor_matches_fru(anchor_component: str, fru_name: str) -> bool:
    """True when a removal anchor's component names this FRU (token overlap)."""

    anchor_tokens = _component_tokens(anchor_component)
    fru_tokens = _component_tokens(fru_name)
    return bool(anchor_tokens and fru_tokens and (anchor_tokens & fru_tokens))


def _anchored_region_bboxes_for_page(
    page: HMMPage,
) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Crop bands keyed by "Removal steps of <component>" anchors (M8.11).

    Each anchor sits at the top of the diagram for the FRU it names, so the band
    [anchor_y, next_anchor_y) isolates that FRU's exploded view even when a larger
    neighbor on the same page would dominate a heading- or area-based band. Returns
    (component_text, padded_bbox); attribution to a concrete FRU is done by the
    caller via name match. None when the page lacks anchors or drawing rects.
    """

    if not page.width or not page.height or not page.removal_anchors or not page.drawing_rects:
        return []
    height = float(page.height)
    width = float(page.width)
    anchors = page.removal_anchors  # sorted (y0, component)
    boundaries = [float(y) for y, _ in anchors] + [height]

    results: list[tuple[str, tuple[float, float, float, float]]] = []
    for index, (anchor_y, component) in enumerate(anchors):
        lo = max(0.0, float(anchor_y))
        hi = min(height, boundaries[index + 1])
        bbox = _drawing_bbox_overlap(page, lo, hi)
        if bbox is not None:
            results.append((component, _padded_bbox(bbox[0], bbox[1], bbox[2], bbox[3], width, height)))
    return results


def _resolve_owner(
    figure: FigureRecord,
    spans: list[tuple[FRUProcedure, int, int]],
    page_info: dict[int, HMMPage],
    procs_by_fru: dict[str, list[FRUProcedure]],
    ordered_starts: list[tuple[int, FRUProcedure]],
) -> FRUProcedure | None:
    if figure.figure_kind in {"region_crop", "region_crop_precise", "region_crop_anchored"} and figure.related_fru_id:
        return _procedure_for_fru(figure.related_fru_id, figure.page, procs_by_fru)
    page = page_info.get(figure.page)
    # No positional data -> legacy page-span containment.
    if page is None or not page.fru_headings:
        if page is not None and not page.fru_headings:
            preceding = _nearest_preceding(figure.page, ordered_starts)
            if preceding is not None:
                return preceding
        return _owning_procedure(figure.page, spans)

    headings = page.fru_headings  # sorted (y0, fru_id)
    if figure.bbox is not None:
        # Embedded image: the band its vertical center falls into.
        y_center = (float(figure.bbox[1]) + float(figure.bbox[3])) / 2.0
        fru_id = _heading_for_y(y_center, headings)
    else:
        # Whole-page raster: the heading band holding the most drawing area.
        fru_id = _dominant_band_fru(headings, page.drawing_bands)

    if fru_id is None:
        # Content sits above the first heading -> continues the preceding FRU.
        return _nearest_preceding(figure.page, ordered_starts, exclusive=True)
    return _procedure_for_fru(fru_id, figure.page, procs_by_fru)


def _heading_for_y(y: float, headings: list[tuple[float, str]]) -> str | None:
    """Return the fru_id of the heading band containing y (heading at or above
    y, nearest). None when y is above every heading."""
    chosen: str | None = None
    for hy, fru_id in headings:
        if hy <= y:
            chosen = fru_id
        else:
            break
    return chosen


def _dominant_band_fru(
    headings: list[tuple[float, str]], drawing_bands: list[tuple[float, float]]
) -> str | None:
    """Return the fru_id whose heading band holds the most drawing area."""
    if not headings:
        return None
    # Build band boundaries: each heading owns [hy, next_hy).
    boundaries = [hy for hy, _ in headings] + [float("inf")]
    area_by_fru: dict[str, float] = {}
    for idx, (hy, fru_id) in enumerate(headings):
        lo, hi = boundaries[idx], boundaries[idx + 1]
        total = 0.0
        for by0, by1 in drawing_bands:
            overlap = min(by1, hi) - max(by0, lo)
            if overlap > 0:
                total += overlap
        area_by_fru[fru_id] = area_by_fru.get(fru_id, 0.0) + total
    # Drawing area above the first heading is NOT owned by any heading on this
    # page (it continues the previous FRU); signal that with None when it wins.
    above_first = 0.0
    first_hy = headings[0][0]
    for by0, by1 in drawing_bands:
        overlap = min(by1, first_hy) - by0
        if overlap > 0:
            above_first += overlap
    best_fru = max(area_by_fru, key=lambda k: area_by_fru[k]) if area_by_fru else None
    if best_fru is None:
        return None
    if above_first > area_by_fru[best_fru]:
        return None
    return best_fru


def _nearest_preceding(
    page: int,
    ordered_starts: list[tuple[int, FRUProcedure]],
    exclusive: bool = False,
) -> FRUProcedure | None:
    """Procedure that continues onto `page` when the page carries no heading.

    Prefer a procedure whose page span actually contains the page (a genuine
    multi-page diagram bleeding onto a heading-less continuation page); only when
    none contains it fall back to the nearest preceding start. Ties on page_start
    break to the narrowest span (Intel/AMD variants share a start)."""
    candidates = [(start, proc) for start, proc in ordered_starts if (start < page if exclusive else start <= page)]
    if not candidates:
        return None
    containing = [(start, proc) for start, proc in candidates if proc.page_end is not None and proc.page_end >= page]
    pool_src = containing or candidates
    best_start = max(start for start, _ in pool_src)
    pool = [proc for start, proc in pool_src if start == best_start]
    return min(pool, key=_span_width)


def _procedure_for_fru(
    fru_id: str, page: int, procs_by_fru: dict[str, list[FRUProcedure]]
) -> FRUProcedure | None:
    """Map a resolved fru_id to a concrete procedure; prefer one whose span
    contains the page, then narrowest span (handles Intel/AMD variants)."""
    candidates = procs_by_fru.get(fru_id, [])
    if not candidates:
        return None
    containing = [
        p for p in candidates
        if p.page_start is not None and p.page_end is not None and p.page_start <= page <= p.page_end
    ]
    pool = containing or candidates
    return min(pool, key=_span_width)


def _span_width(proc: FRUProcedure) -> int:
    """Page-span width for narrowest-span tiebreaks; 0 when starts are unknown."""
    start = proc.page_start or 0
    end = proc.page_end if proc.page_end is not None else start
    return end - start


def _owning_procedure(
    page: int, spans: list[tuple[FRUProcedure, int, int]]
) -> FRUProcedure | None:
    best: FRUProcedure | None = None
    best_width = None
    for proc, start, end in spans:
        if start <= page <= end:
            width = end - start
            if best_width is None or width < best_width:
                best = proc
                best_width = width
    return best


def extract_prerequisites(text: str) -> list[str]:
    """Extract prerequisite FRU references from a procedure section."""

    lowered = text.lower()
    starts = [
        lowered.find(marker)
        for marker in ("before removing", "before you remove", "for access, remove", "remove the following")
        if lowered.find(marker) >= 0
    ]
    if not starts:
        return []
    window = text[min(starts) : min(starts) + 1400]

    prerequisites: list[str] = []
    seen: set[str] = set()
    for match in _FRU_REF_RE.finditer(window):
        fru_id = match.group("fru_id")
        if not _looks_like_fru_id(fru_id):
            continue
        value = f"{fru_id} {_clean_name(match.group('name'))}"
        if value not in seen:
            seen.add(value)
            prerequisites.append(value)
    return prerequisites


def _find_sections(pages: list[HMMPage]) -> list[_Section]:
    combined, page_offsets = _combine_pages(pages)
    figure_pages = {page.page for page in pages if _page_has_figure(page)}
    heading_matches = [
        match
        for match in _FRU_HEADING_RE.finditer(combined)
        if _looks_like_fru_id(match.group("fru_id"))
        and not _is_prerequisite_list_item(combined, match.start())
    ]

    sections: list[_Section] = []
    for index, match in enumerate(heading_matches):
        start = match.start()
        end = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(combined)
        raw_text = combined[start:end]
        text = raw_text.strip()
        if not _looks_like_procedure(text):
            continue
        page_start = _page_for_offset(start, page_offsets)
        page_end = _page_for_offset(max(start, end - 1), page_offsets)
        has_figure = any(page in figure_pages for page in range(page_start, page_end + 1))
        page_start = _page_for_offset(start, page_offsets)
        page_end = _page_for_offset(max(start, end - 1), page_offsets)
        has_figure = any(page in figure_pages for page in range(page_start, page_end + 1))
        base_section = _Section(
            fru_id=match.group("fru_id"),
            fru_name=_clean_name(match.group("name")),
            page_start=page_start,
            page_end=page_end,
            text=text,
            raw_text=raw_text,
            start_offset=start,
            page_offsets=page_offsets,
            has_figure=has_figure,
        )
        # Recompute per-variant has_figure from the variant's own page span.
        for variant in _split_variant_sections(base_section, figure_pages):
            sections.append(variant)
    return sections


def _combine_pages(pages: list[HMMPage]) -> tuple[str, list[tuple[int, int]]]:
    chunks: list[str] = []
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for page in pages:
        marker = f"\n\n[[PAGE {page.page}]]\n"
        chunks.append(marker)
        cursor += len(marker)
        offsets.append((cursor, page.page))
        chunks.append(page.text)
        cursor += len(page.text)
    return "".join(chunks), offsets


def _page_for_offset(offset: int, page_offsets: list[tuple[int, int]]) -> int:
    current = page_offsets[0][1] if page_offsets else 1
    for start, page in page_offsets:
        if start > offset:
            break
        current = page
    return current


def _looks_like_fru_id(fru_id: str) -> bool:
    return int(fru_id) >= 1000


def _looks_like_procedure(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _PROCEDURE_MARKERS)


def _is_prerequisite_list_item(text: str, start: int) -> bool:
    prior_lines = [line.strip().lower() for line in text[:start].splitlines() if line.strip()]
    previous_line = prior_lines[-1] if prior_lines else ""
    return "following frus" in previous_line or "remove these frus" in previous_line


def _extract_steps(section: _Section) -> list[str]:
    return [step.text for step in _extract_step_records_from_section(section)]


def _extract_step_records(manual: ManualMetadata, section: _Section) -> list[FRUStepRecord]:
    steps = _extract_step_records_from_section(section)
    records: list[FRUStepRecord] = []
    for index, step in enumerate(steps, start=1):
        citation = Citation(
            manual_id=manual.manual_id,
            source_url=manual.source_url,
            page_start=step.page,
            page_end=step.page,
            section=f"{section.fru_id} {section.fru_name}",
            section_id=section.fru_id,
        )
        records.append(
            FRUStepRecord(
                step_index=index,
                text=step.text,
                citation=citation,
                citation_source="text_offset",
                step_kind=step.kind,
            )
        )
    return records


@dataclass(frozen=True)
class _ExtractedStep:
    text: str
    page: int
    kind: str = "removal_step"


_STEP_START_MARKERS = ("note:", "notes:", "when installing:", "attention:")
_STEP_ACTION_STARTS = (
    "remove",
    "disconnect",
    "detach",
    "lift",
    "loosen",
    "install",
    "attach",
    "connect",
    "ensure",
    "route",
    "unplug",
    "disable",
    "slide",
    "pull",
    "open",
    "turn",
    "peel",
    "grasp",
    "press",
    "apply",
    "align",
    "reconnect",
    "replace",
    "insert",
    "pivot",
    "put",
    "push",
    "place",
    "take",
    "hold",
    "rotate",
    "flip",
    "fold",
    "release",
)
_BULLET_RE = re.compile(r"^[•·•\-*]\s+")


def _is_step_noise_line(line: str) -> bool:
    lowered = line.lower()
    if re.fullmatch(r"[0-9]+", line):
        return True
    if re.fullmatch(r"[a-d]", lowered):
        return True
    if re.fullmatch(r"(https?://|www\.)?[\w.-]+\.(com|cn|net|org|io|gov)(/\S*)?", lowered):
        return True
    if "hardware maintenance manual" in lowered:
        return True
    if lowered.startswith("chapter "):
        return True
    if re.match(r"(removal|installation) steps of", lowered):
        return True
    return False


def _starts_new_step(line: str, prev_closed: bool) -> bool:
    lowered = line.lower()
    if re.match(r"^\d+\.", line):
        return True
    if lowered.startswith(_STEP_START_MARKERS):
        return True
    first = lowered.split(" ", 1)[0].strip(".:,")
    return first in _STEP_ACTION_STARTS and prev_closed


_INSTALL_BLOCK_STARTS = ("when installing", "after installing", "installation steps")
_REMOVAL_VERBS = (
    "remove",
    "disconnect",
    "detach",
    "lift",
    "loosen",
    "unplug",
    "slide",
    "pull",
    "peel",
    "grasp",
    "turn over",
    "pivot",
    "release",
    "open",
    "take out",
    "put",
    "push",
    "place",
    "rotate",
    "flip",
    "fold",
)
_SPEC_TABLE_RE = re.compile(
    r"^(step\b|screw \(quantity\)|color\b|torque\b|m\d|0\.\d+\s*(\+/-|nm)|table \d)", re.I
)
_WARNING_RE = re.compile(r"^(danger|caution|attention|warning)\b", re.I)
# Numbered lines inside an image-only section are sometimes a software/BIOS
# sub-procedure (color-calibration, UEFI settings), not a physical FRU removal.
# These must not be tagged removal_step even though they start with a verb like
# "open"/"go"/"select" (AGENTS.md section 6.4: don't fabricate removal steps).
_NON_REMOVAL_CONTEXT_RE = re.compile(
    r"\b(x-rite|color assistant|color profile|color calibration|uefi|bios|"
    r"connected to (the )?(internet|network)|restore profiles|setup utility|"
    r"operating system|driver|app\b|application|software|reinstall|re-install)\b",
    re.I,
)


def _classify_step_kind(text: str, install_mode: bool) -> str:
    """Classify an extracted step so image-only removals don't masquerade as steps.

    Lenovo HMM removal procedures are frequently a single exploded-view image
    with no numbered text. The only nearby text is then a "When installing:"
    block, a screw/torque spec table, or a DANGER/CAUTION warning. Tagging the
    kind lets gold selection keep only genuine textual removal steps and lets
    downstream tools avoid presenting install notes as removal steps (AGENTS.md
    section 6.4: diagrams are retrieval targets, not step sources).
    """

    lowered = text.strip().lower()
    if _WARNING_RE.match(lowered):
        return "warning"
    if _SPEC_TABLE_RE.match(lowered):
        return "spec_table"
    if install_mode or lowered.startswith(_INSTALL_BLOCK_STARTS):
        return "install_note"
    if _NON_REMOVAL_CONTEXT_RE.search(lowered):
        return "other"
    if re.match(r"^\d+\.\s*(" + "|".join(_REMOVAL_VERBS) + r")\b", lowered):
        return "removal_step"
    first = lowered.split(" ", 1)[0].strip(".:,")
    if first in {verb.split()[0] for verb in _REMOVAL_VERBS} and "install" not in lowered:
        return "removal_step"
    if re.fullmatch(r"(\d+[a-z]\s*)+", lowered) or re.fullmatch(r"[a-z\d ]{0,8}", lowered):
        return "image_only_marker"
    return "other"


_CROSS_REF_RE = re.compile(
    r"removal steps are (similar|the same)|similar to that of|same as (that of|the)",
    re.I,
)


def _classify_presentation(section: _Section, step_records: list[FRUStepRecord]) -> str:
    """Classify how a removal procedure is presented (AGENTS.md section 6.4).

    Most ThinkPad HMM removal procedures are exploded-view figures with no
    textual steps; the section's only text is a screw table, a "When installing"
    note, or a cross-reference to another model's procedure. Telling these apart
    lets the runtime return the figure instead of fabricating steps from
    unrelated prose.

    - cross_ref: the section defers to another procedure ("similar to that of
      Intel models") and has no real removal-step text of its own.
    - image_only: a figure is present and there is no textual removal step.
    - interleaved: a figure is present and at least one textual removal step.
    - text_only: textual removal steps with no figure.
    """

    removal_steps = sum(1 for record in step_records if record.step_kind == "removal_step")
    if removal_steps == 0 and _CROSS_REF_RE.search(section.text):
        return "cross_ref"
    if section.has_figure and removal_steps == 0:
        return "image_only"
    if section.has_figure and removal_steps >= 1:
        return "interleaved"
    if not section.has_figure and removal_steps >= 1:
        return "text_only"
    # No figure detected and no textual removal step: treat as cross_ref when the
    # text defers elsewhere, otherwise image_only is wrong (no figure) so fall
    # back to text_only with empty steps — callers see zero removal steps.
    if _CROSS_REF_RE.search(section.text):
        return "cross_ref"
    return "text_only"


def _extract_step_records_from_section(section: _Section) -> list[_ExtractedStep]:
    """Split a procedure section into logical steps, merging wrapped lines.

    Raw HMM text wraps a single instruction across physical lines. Emitting one
    record per physical line produces dangling fragments ("insert the battery
    into", "the following illustration"). Here a numbered prefix, a known marker
    (Note:/When installing:), a bullet, or a sentence-initial action verb starts
    a new logical step; unnumbered non-noise lines continue the current step.
    Page numbers, footers, chapter headers, and single bullet letters are
    dropped. Each merged step's page is its first line's page.
    """

    extracted: list[_ExtractedStep] = []
    parts: list[str] = []
    page: int | None = None
    last_closed = True
    in_steps = False
    install_mode = False

    def flush() -> None:
        nonlocal parts, page
        if parts and page is not None:
            text = _clean_name(" ".join(parts))
            if text:
                extracted.append(
                    _ExtractedStep(text=text, page=page, kind=_classify_step_kind(text, install_mode))
                )
        parts = []
        page = None

    for match in re.finditer(r"[^\n]+", section.raw_text):
        clean = _clean_name(match.group(0))
        bullet = bool(_BULLET_RE.match(clean))
        line = _BULLET_RE.sub("", clean).strip()
        lowered = line.lower()
        if "removal steps" in lowered:
            in_steps = True
            install_mode = False
            continue
        if not in_steps:
            continue
        if not line or _FRU_HEADING_RE.match(line):
            continue
        if lowered.startswith("[[page "):
            continue
        if lowered.startswith(("before removing", "before you remove", "remove the following")):
            continue
        if _is_step_noise_line(line):
            continue
        prev_closed = (not parts) or last_closed
        if bullet or _starts_new_step(line, prev_closed):
            flush()
            if lowered.startswith(_INSTALL_BLOCK_STARTS):
                install_mode = True
            page = _page_for_offset(section.start_offset + match.start(), section.page_offsets)
            parts = [line]
        else:
            if not parts:
                page = _page_for_offset(section.start_offset + match.start(), section.page_offsets)
            parts.append(line)
        last_closed = match.group(0).rstrip().endswith((".", ":", "!", "?"))
        if len(extracted) >= 50:
            break
    flush()
    return extracted[:50]


def _clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .;,")
