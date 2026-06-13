from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import yaml


def _load_script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "thinkpad_prepare_human_gold_review.py"
    spec = importlib.util.spec_from_file_location("thinkpad_prepare_human_gold_review", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_review_pack_outputs_pending_copyright_light_candidates(tmp_path: Path) -> None:
    module = _load_script()
    manifest = _write_manifest(tmp_path)
    extracted = _write_extracted(tmp_path)

    pack = module.build_review_pack(manifest, extracted)

    assert pack["version"] == "m8_4a_review_pack"
    assert pack["candidate_count"] >= 10
    assert all(item["review_status"] == "pending" for item in pack["candidates"])
    assert all(item["verified_pages"] == [] for item in pack["candidates"])
    assert "Replace the system board" not in json.dumps(pack, ensure_ascii=False)

    positive = [item for item in pack["candidates"] if item["expected_status"] == "ok"]
    assert positive
    for item in positive:
        assert item["manual_id"]
        assert item["candidate_pages"]
        assert item["record_type"]
        assert item["identifier"]
        assert item["pdf_local_path"].startswith("data/manuals/")

    negative = [item for item in pack["candidates"] if item["category"] == "negative"]
    assert len(negative) == 2
    assert all(item["candidate_pages"] == [] for item in negative)


def test_build_review_pack_requires_extracted_inputs(tmp_path: Path) -> None:
    module = _load_script()
    manifest = _write_manifest(tmp_path)
    extracted = tmp_path / "missing"

    try:
        module.build_review_pack(manifest, extracted)
    except FileNotFoundError as exc:
        assert "extracted-dir does not exist" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_render_review_markdown_marks_pack_as_review_only(tmp_path: Path) -> None:
    module = _load_script()
    pack = module.build_review_pack(_write_manifest(tmp_path), _write_extracted(tmp_path))

    rendered = module.render_review_markdown(pack)

    assert "not a committed human gold set" in rendered
    assert "Review status: `pending`" in rendered
    assert "Verified pages: `[]`" in rendered


def _write_manifest(tmp_path: Path) -> Path:
    manuals = []
    manual_ids = [
        "thinkpad_t14_gen2_p14s_gen2_hmm",
        "thinkpad_t14_gen3_p14s_gen3_hmm",
        "thinkpad_t480_hmm",
        "thinkpad_t490_hmm",
        "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
        "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
        "thinkpad_e14_gen2_e15_gen2_hmm",
        "thinkpad_p1_gen4_x1_extreme_gen4_hmm",
    ]
    for index, manual_id in enumerate(manual_ids, start=1):
        manuals.append(
            {
                "manual_id": manual_id,
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


def _write_extracted(tmp_path: Path) -> Path:
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    manual_ids = [
        "thinkpad_t14_gen2_p14s_gen2_hmm",
        "thinkpad_t14_gen3_p14s_gen3_hmm",
        "thinkpad_t480_hmm",
        "thinkpad_t490_hmm",
        "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm",
        "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm",
        "thinkpad_e14_gen2_e15_gen2_hmm",
        "thinkpad_p1_gen4_x1_extreme_gen4_hmm",
    ]
    procedures = []
    tables = []
    warnings = []
    figures = []
    edges = []
    for index, manual_id in enumerate(manual_ids, start=1):
        fru_id = f"10{index}0"
        procedures.append(
            {
                "manual_id": manual_id,
                "procedure_id": f"{manual_id}_fru_{fru_id}",
                "fru_id": fru_id,
                "fru_name": "Built-in battery",
                "citation": {"page_start": 10 + index, "page_end": 11 + index},
            }
        )
        edges.append(
            {
                "manual_id": manual_id,
                "source_fru_id": fru_id,
                "required_fru_id": "1020",
                "citation": {"page_start": 10 + index, "page_end": 11 + index},
            }
        )
        tables.append(
            {
                "manual_id": manual_id,
                "record_id": f"{manual_id}_error",
                "table_type": "error_code",
                "page": 30 + index,
                "row": {
                    "Symptom or error": f"0177 synthetic error {index}",
                    "FRU or action": "Replace the system board.",
                },
            }
        )
        tables.append(
            {
                "manual_id": manual_id,
                "record_id": f"{manual_id}_screw",
                "table_type": "screw_spec",
                "page": 40 + index,
                "row": {"Screw (quantity)": "M2 x 3 mm"},
            }
        )
        warnings.append(
            {
                "manual_id": manual_id,
                "warning_id": f"{manual_id}_warning",
                "page": 50 + index,
                "warning_level": "CAUTION",
                "related_component": "battery",
            }
        )
        figures.append(
            {
                "manual_id": manual_id,
                "image_id": f"{manual_id}_figure",
                "page": 60 + index,
                "caption": "Synthetic figure candidate",
            }
        )

    _write_jsonl(extracted / "fru_procedures.jsonl", procedures)
    _write_jsonl(extracted / "tables.jsonl", tables)
    _write_jsonl(extracted / "warnings.jsonl", warnings)
    _write_jsonl(extracted / "figures.jsonl", figures)
    _write_jsonl(extracted / "dependency_edges.jsonl", edges)
    return extracted


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
