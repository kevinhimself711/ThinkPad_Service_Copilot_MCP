from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml


def _load_script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "thinkpad_prepare_step_citation_review.py"
    spec = importlib.util.spec_from_file_location("thinkpad_prepare_step_citation_review", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_step_review_pack_outputs_pending_step_annotations(tmp_path: Path) -> None:
    module = _load_script()
    manifest = _write_manifest(tmp_path)
    extracted = _write_extracted(tmp_path, include_step_records=True)

    pack = module.build_step_review_pack(manifest, extracted, target_count=2)

    assert pack["version"] == "m8_5a_step_citation_review_pack"
    assert pack["candidate_count"] == 2
    assert pack["multi_page_candidate_count"] >= 1
    assert all(item["review_status"] == "pending" for item in pack["candidates"])
    assert all(item["candidate_steps"] for item in pack["candidates"])
    first = pack["candidates"][0]
    assert first["candidate_steps"][0]["review_status"] == "pending"
    assert first["candidate_steps"][0]["verified_page"] is None
    assert "Replace the system board" not in json.dumps(pack, ensure_ascii=False)


def test_render_step_review_markdown_explains_step_statuses(tmp_path: Path) -> None:
    module = _load_script()
    pack = module.build_step_review_pack(
        _write_manifest(tmp_path),
        _write_extracted(tmp_path, include_step_records=True),
        target_count=1,
    )

    rendered = module.render_step_review_markdown(pack)

    assert "not a committed human gold set" in rendered
    assert "Step status values" in rendered
    assert "Candidate page" in rendered
    assert "Verified page: ``" in rendered


def test_build_step_review_pack_requires_step_records(tmp_path: Path) -> None:
    module = _load_script()

    with pytest.raises(ValueError, match="no step_records"):
        module.build_step_review_pack(
            _write_manifest(tmp_path),
            _write_extracted(tmp_path, include_step_records=False),
            target_count=1,
        )


def _write_manifest(tmp_path: Path) -> Path:
    manuals = []
    for index in range(1, 3):
        manuals.append(
            {
                "manual_id": f"manual_{index}",
                "title": f"Manual {index}",
                "models": [f"ThinkPad Model {index}"],
                "generations": [f"Gen {index}"],
                "machine_types": [f"20{index:02d}"],
                "source_type": "lenovo_official",
                "source_url": f"https://download.lenovo.com/manual_{index}.pdf",
                "local_pdf_path": f"data/manuals/manual_{index}.pdf",
            }
        )
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump({"manuals": manuals}), encoding="utf-8")
    return path


def _write_extracted(tmp_path: Path, include_step_records: bool) -> Path:
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    procedures = []
    for index in range(1, 3):
        record = {
            "manual_id": f"manual_{index}",
            "procedure_id": f"manual_{index}_fru_10{index}0",
            "fru_id": f"10{index}0",
            "fru_name": "Built-in battery",
            "citation": {
                "manual_id": f"manual_{index}",
                "source_url": f"https://download.lenovo.com/manual_{index}.pdf",
                "page_start": 70,
                "page_end": 71,
                "section": f"10{index}0 Built-in battery",
                "section_id": f"10{index}0",
            },
            "steps": ["Disconnect battery connector.", "Remove battery screws."],
        }
        if include_step_records:
            record["step_records"] = [
                {
                    "step_index": 1,
                    "text": "Disconnect battery connector.",
                    "citation": {
                        "manual_id": f"manual_{index}",
                        "source_url": f"https://download.lenovo.com/manual_{index}.pdf",
                        "page_start": 70,
                        "page_end": 70,
                        "section_id": f"10{index}0",
                    },
                    "citation_source": "text_offset",
                },
                {
                    "step_index": 2,
                    "text": "Remove battery screws.",
                    "citation": {
                        "manual_id": f"manual_{index}",
                        "source_url": f"https://download.lenovo.com/manual_{index}.pdf",
                        "page_start": 71 if index == 1 else 70,
                        "page_end": 71 if index == 1 else 70,
                        "section_id": f"10{index}0",
                    },
                    "citation_source": "text_offset",
                },
            ]
        procedures.append(record)
    (extracted / "fru_procedures.jsonl").write_text(
        "\n".join(json.dumps(record) for record in procedures) + "\n",
        encoding="utf-8",
    )
    return extracted
