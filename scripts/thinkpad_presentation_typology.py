#!/usr/bin/env python
"""Read-only M8.6 research: classify how each FRU removal procedure is presented.

Builds a presentation typology over all 8 HMMs by walking each FRU section
(heading to next heading) and measuring, within that section's page span:
text removal-step lines, numbered lines, and vector-drawing / embedded-image
density. Vector line drawings (get_drawings) are the dominant figure form in
these manuals, so embedded-image counts alone miss most diagrams.

Output is a typology summary; it writes no manual prose to disk.
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.thinkpad.manifest import load_manifest  # noqa: E402

FRU_HEAD = re.compile(r"^\s*([1-9]\d{3})\s+([A-Za-z][^\n]{2,80})$")
REMOVAL = re.compile(r"removal steps", re.I)
NUM_STEP = re.compile(r"^\d+\.\s+\S")
_VERBS = (
    "remove", "disconnect", "detach", "lift", "loosen", "unplug", "slide",
    "pull", "peel", "grasp", "turn", "pivot", "release", "put", "push",
    "open", "press", "rotate", "flip", "fold",
)


def _is_step_line(text: str) -> bool:
    if NUM_STEP.match(text):
        return True
    first = text.split(" ", 1)[0].lower().strip(".:,")
    return first in _VERBS


def main() -> int:
    import fitz  # type: ignore

    manuals = load_manifest("data/manifests/manuals_manifest.yaml")
    overall: Counter[str] = Counter()
    per_manual: dict[str, Counter[str]] = {}
    examples: dict[str, list[str]] = defaultdict(list)

    for man in manuals:
        d = fitz.open(man.local_pdf_path)
        page_drawings: dict[int, int] = {}
        page_lines: dict[int, list[str]] = {}
        for pi in range(len(d)):
            page = d[pi]
            try:
                draw = len(page.get_drawings())
            except Exception:
                draw = 0
            try:
                imgs = len(page.get_images(full=True))
            except Exception:
                imgs = 0
            # A page "has a figure" if it carries many vector strokes (line art)
            # OR at least one embedded raster image. t14_gen3 uses raster images,
            # most others use vector drawings, so we must count both.
            page_drawings[pi + 1] = max(draw, imgs * 50)
            page_lines[pi + 1] = [
                ln.strip() for ln in (page.get_text("text") or "").splitlines() if ln.strip()
            ]
        d.close()

        mc: Counter[str] = Counter()
        for pn, lines in page_lines.items():
            for i, ln in enumerate(lines):
                if not REMOVAL.search(ln):
                    continue
                window: list[str] = []
                for nxt in lines[i + 1 :]:
                    if FRU_HEAD.match(nxt) or REMOVAL.search(nxt):
                        break
                    window.append(nxt)
                step_lines = sum(1 for w in window if _is_step_line(w))
                draws = page_drawings.get(pn, 0)
                has_fig = draws >= 5
                if has_fig and step_lines == 0:
                    cls = "IMAGE_ONLY"
                elif has_fig and step_lines >= 1:
                    cls = "INTERLEAVED"
                elif not has_fig and step_lines >= 1:
                    cls = "TEXT_ONLY"
                else:
                    cls = "OTHER_NO_FIG_NO_STEP"
                mc[cls] += 1
                overall[cls] += 1
                if len(examples[cls]) < 8:
                    examples[cls].append(f"{man.manual_id[:22]} p{pn} steps={step_lines} draw={draws}: {ln[:46]}")
        per_manual[man.manual_id] = mc

    tot = sum(overall.values())
    print("=== OVERALL removal-procedure presentation types (8 manuals) ===")
    for k, v in overall.most_common():
        print(f"  {k:22} {v:4}  ({100*v//max(tot,1)}%)")
    print(f"  TOTAL removal-step sections: {tot}")
    print("\n=== per manual ===")
    for mid, c in per_manual.items():
        print(f"  {mid[:34]:34} {dict(c)}")
    print("\n=== examples ===")
    for k in ("IMAGE_ONLY", "INTERLEAVED", "TEXT_ONLY", "OTHER_NO_FIG_NO_STEP"):
        print(f"\n[{k}]")
        for e in examples.get(k, []):
            print(f"  {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
