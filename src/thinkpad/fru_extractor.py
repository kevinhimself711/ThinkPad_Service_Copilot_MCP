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
) -> tuple[list[FigureRecord], list[FRUProcedure]]:
    """Link figures to the FRU procedure whose page span contains them.

    Figures are extracted per page with no FRU association (related_fru_id is
    None). For IMAGE_ONLY procedures the correct answer to a "removal steps"
    query is the removal diagram, so each figure must know which FRU it belongs
    to. A figure's page is matched to the procedure whose [page_start, page_end]
    span contains it; when several procedures overlap a page (variant
    sub-procedures or multiple FRUs on one page), the narrowest containing span
    wins, which prefers the most specific owner. Returns updated copies; figures
    with no containing procedure are returned unchanged.
    """

    spans = [
        (proc, proc.page_start, proc.page_end)
        for proc in procedures
        if proc.page_start is not None and proc.page_end is not None
    ]
    images_by_proc_id: dict[str, list[str]] = {}
    updated_figures: list[FigureRecord] = []
    for figure in figures:
        owner = _owning_procedure(figure.page, spans)
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

    updated_procedures = [
        replace(proc, related_image_ids=images_by_proc_id.get(proc.procedure_id, list(proc.related_image_ids)))
        if proc.procedure_id in images_by_proc_id
        else proc
        for proc in procedures
    ]
    return updated_figures, updated_procedures


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
