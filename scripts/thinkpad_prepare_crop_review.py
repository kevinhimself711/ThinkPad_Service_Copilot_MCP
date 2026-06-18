"""Prepare a local M8.10 residual crop review pack.

The output is intentionally copyright-light: no PDF text, no rendered images,
and no provider output beyond short component names already present in the local
evaluation rows. The JSON/Markdown outputs belong under ignored data/eval paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare M8.10 residual crop review metadata.")
    parser.add_argument("--extracted-dir", default="data/extracted/m3")
    parser.add_argument("--m8-9-full", default="data/eval/m8_9_vision_live_full_final.jsonl")
    parser.add_argument("--m8-9-targeted", default="data/eval/m8_9_vision_live_targeted_regions_final.jsonl")
    parser.add_argument("--output", default="data/eval/m8_10_residual_crop_review.json")
    parser.add_argument("--markdown-output", default="data/eval/m8_10_residual_crop_review.md")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    extracted = Path(args.extracted_dir)
    figures = {
        row["image_id"]: row
        for row in _load_jsonl(extracted / "figures.jsonl")
        if row.get("image_id")
    }
    procedures = [
        row
        for row in _load_jsonl(extracted / "fru_procedures.jsonl")
        if row.get("presentation_type") == "image_only"
    ]
    proc_by_key = {(row.get("manual_id"), row.get("fru_id")): row for row in procedures}

    failure_keys = _failed_keys(Path(args.m8_9_full)) | _failed_keys(Path(args.m8_9_targeted))
    zero_image_keys = {
        (row.get("manual_id"), row.get("fru_id"))
        for row in procedures
        if not row.get("related_image_ids")
    }
    cases = []
    for manual_id, fru_id in sorted(failure_keys | zero_image_keys):
        proc = proc_by_key.get((manual_id, fru_id))
        if not proc:
            continue
        related = []
        for image_id in proc.get("related_image_ids") or []:
            fig = figures.get(str(image_id)) or {}
            related.append(
                {
                    "image_id": image_id,
                    "figure_kind": fig.get("figure_kind") or "unknown",
                    "page": fig.get("page"),
                    "bbox": fig.get("bbox"),
                    "source_image_id": fig.get("source_image_id"),
                    "related_fru_id": fig.get("related_fru_id"),
                }
            )
        cases.append(
            {
                "case_id": f"m8_10_{manual_id}_{fru_id}",
                "manual_id": manual_id,
                "fru_id": fru_id,
                "fru_name": proc.get("fru_name"),
                "page_start": proc.get("page_start"),
                "page_end": proc.get("page_end"),
                "source": _source_label((manual_id, fru_id), failure_keys, zero_image_keys),
                "related_images": related,
                "review_status": "pending",
                "review_label": "",
                "reviewer_notes": "",
            }
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"cases": cases}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = Path(args.markdown_output)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(_markdown(cases), encoding="utf-8")
    print(f"Wrote {len(cases)} review cases to {output} and {markdown}")
    return 0


def _source_label(
    key: tuple[Any, Any],
    failure_keys: set[tuple[Any, Any]],
    zero_image_keys: set[tuple[Any, Any]],
) -> str:
    labels = []
    if key in failure_keys:
        labels.append("m8_9_failure")
    if key in zero_image_keys:
        labels.append("zero_image")
    return "+".join(labels) or "unknown"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _failed_keys(path: Path) -> set[tuple[Any, Any]]:
    return {
        (row.get("manual"), row.get("fru_id"))
        for row in _load_jsonl(path)
        if row.get("fig_ok") is False
    }


def _markdown(cases: list[dict[str, Any]]) -> str:
    lines = [
        "# M8.10 Residual Crop Review",
        "",
        "Allowed review labels: `correct_crop`, `wrong_neighbor`, `scorer_false_negative`, `ambiguous`.",
        "Do not copy Lenovo manual text into this file.",
        "",
    ]
    for case in cases:
        lines.extend(
            [
                f"## {case['case_id']}",
                "",
                f"- Manual: `{case['manual_id']}`",
                f"- FRU: `{case['fru_id']}` `{case['fru_name']}`",
                f"- Pages: `{case['page_start']}`-`{case['page_end']}`",
                f"- Source: `{case['source']}`",
                "- Related images:",
            ]
        )
        if case["related_images"]:
            for image in case["related_images"]:
                lines.append(
                    f"  - `{image['image_id']}` kind=`{image['figure_kind']}` page=`{image['page']}` "
                    f"bbox=`{image['bbox']}` source=`{image['source_image_id']}`"
                )
        else:
            lines.append("  - none")
        lines.extend(
            [
                "- review_status: pending",
                "- review_label: ",
                "- reviewer_notes: ",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
