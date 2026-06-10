#!/usr/bin/env python
"""Discover official Lenovo HMM PDFs for the ThinkPad M1 spike."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from src.thinkpad.lenovo import (
    M1_MANUAL_TARGETS,
    discover_hmm_candidates_from_product_page,
    extract_manual_candidates,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover official Lenovo HMM PDF URLs.")
    parser.add_argument(
        "--target-set",
        choices=["m1"],
        default="m1",
        help="Built-in target set to discover.",
    )
    parser.add_argument(
        "--product-page-url",
        action="append",
        default=[],
        help="Additional Lenovo product self-repair page URL to inspect.",
    )
    parser.add_argument(
        "--api-payload",
        help="Optional Lenovo API JSON payload to parse instead of making network calls.",
    )
    parser.add_argument(
        "--output",
        help="Write discovered manifest YAML to this path. Without this, prints JSON.",
    )
    return parser.parse_args()


def _candidate_to_manifest_entry(target: Any, candidate: Any | None) -> dict[str, Any]:
    return {
        "manual_id": target.manual_id,
        "title": candidate.title if candidate else target.title,
        "models": target.models,
        "generations": target.generations,
        "machine_types": target.machine_types,
        "year": target.year,
        "edition": None,
        "source_type": "lenovo_official",
        "source_url": candidate.url if candidate else "",
        "product_page_url": target.product_page_url,
        "local_pdf_path": target.local_pdf_path,
        "document_type": "hmm",
        "language": candidate.language if candidate and candidate.language else "en",
        "checksum_sha256": None,
        "file_size_bytes": None,
        "spike_status": "discovered" if candidate else "discovery_failed",
        "notes": [] if candidate else ["No HMM PDF candidate was returned by Lenovo discovery."],
    }


def _discover_targets() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for target in M1_MANUAL_TARGETS:
        try:
            candidates = discover_hmm_candidates_from_product_page(target.product_page_url)
            candidate = candidates[0] if candidates else None
            entry = _candidate_to_manifest_entry(target, candidate)
            if len(candidates) > 1:
                entry["notes"].append(f"Multiple HMM candidates found; selected {candidate.url}.")
            entries.append(entry)
        except Exception as exc:
            entry = _candidate_to_manifest_entry(target, None)
            entry["notes"].append(f"Discovery error: {type(exc).__name__}: {exc}")
            entries.append(entry)
    return entries


def main() -> int:
    args = parse_args()

    if args.api_payload:
        payload = json.loads(Path(args.api_payload).read_text(encoding="utf-8"))
        candidates = extract_manual_candidates(payload)
        print(json.dumps([candidate.__dict__ for candidate in candidates], ensure_ascii=False, indent=2))
        return 0

    entries = _discover_targets()

    for product_page_url in args.product_page_url:
        try:
            candidates = discover_hmm_candidates_from_product_page(product_page_url)
            for index, candidate in enumerate(candidates, 1):
                entries.append(
                    {
                        "manual_id": f"custom_hmm_{len(entries) + index}",
                        "title": candidate.title,
                        "models": [],
                        "generations": [],
                        "machine_types": [],
                        "year": None,
                        "edition": None,
                        "source_type": "lenovo_official",
                        "source_url": candidate.url,
                        "product_page_url": product_page_url,
                        "local_pdf_path": f"data/manuals/{Path(candidate.url).name}",
                        "document_type": "hmm",
                        "language": candidate.language or "en",
                        "checksum_sha256": None,
                        "file_size_bytes": None,
                        "spike_status": "discovered",
                        "notes": ["Custom target; fill models/generations/machine_types before ingestion."],
                    }
                )
        except Exception as exc:
            entries.append(
                {
                    "manual_id": f"custom_hmm_{len(entries) + 1}",
                    "title": "Discovery failed",
                    "models": [],
                    "generations": [],
                    "machine_types": [],
                    "year": None,
                    "edition": None,
                    "source_type": "lenovo_official",
                    "source_url": "",
                    "product_page_url": product_page_url,
                    "local_pdf_path": "data/manuals/manual.pdf",
                    "document_type": "hmm",
                    "language": "en",
                    "checksum_sha256": None,
                    "file_size_bytes": None,
                    "spike_status": "discovery_failed",
                    "notes": [f"Discovery error: {type(exc).__name__}: {exc}"],
                }
            )

    payload = {"manuals": entries}
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(f"Wrote discovered manifest: {output_path}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
