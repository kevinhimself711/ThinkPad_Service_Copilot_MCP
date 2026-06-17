from __future__ import annotations

import json
from pathlib import Path

from src.libs.llm.base_vision_llm import ImageInput
from src.thinkpad import vision_steps as vs


class _FakeVision:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0

    def chat_with_image(self, text, image, messages=None, trace=None, **kwargs):
        self.calls += 1

        class _R:
            content = self.content

        return _R()


class _RaisingVision:
    def chat_with_image(self, text, image, messages=None, trace=None, **kwargs):
        raise RuntimeError("provider failure")


def _procedure() -> dict:
    return {
        "procedure_id": "m_fru_1070",
        "fru_name": "Thermal fan assembly",
        "related_image_ids": ["fig_a"],
        "citation": {"manual_id": "m", "page_start": 78},
    }


def test_parse_step_lines_strips_numbering_and_rejects_spec_leaks():
    content = (
        "1. Disconnect the fan cable from the system board.\n"
        "2. Loosen the 3 screws (M2 x 4 mm, 0.18 Nm).\n"
        "3. Lift the thermal fan assembly off the heatsink.\n"
        "Torque: 0.18 Nm\n"
        "- Remove the bracket.\n"
        "FRU 1080 audio board\n"
    )
    steps = vs._parse_step_lines(content)
    assert steps == [
        "Disconnect the fan cable from the system board.",
        "Lift the thermal fan assembly off the heatsink.",
        "Remove the bracket.",
    ]


def test_reconstruct_steps_marks_unverified_and_no_specs():
    vision = _FakeVision("1. Disconnect the cable.\n2. Lift the fan.")
    steps = vs.reconstruct_steps(vision, [ImageInput(data=b"x")], _procedure())
    assert [s["text"] for s in steps] == ["Disconnect the cable.", "Lift the fan."]
    assert all(s["step_kind"] == vs.VISION_STEP_KIND for s in steps)
    assert all(s["verified"] is False for s in steps)
    assert all(s["citation_source"] == vs.VISION_CITATION_SOURCE for s in steps)


def test_reconstruct_steps_empty_on_no_images():
    assert vs.reconstruct_steps(_FakeVision("x"), [], _procedure()) == []


def test_reconstruct_steps_empty_on_provider_failure():
    assert vs.reconstruct_steps(_RaisingVision(), [ImageInput(data=b"x")], _procedure()) == []


def test_get_or_reconstruct_caches_and_skips_second_call(tmp_path: Path, monkeypatch):
    cache_file = tmp_path / "vision_steps.jsonl"
    vision = _FakeVision("1. Disconnect the cable.")
    figures = {"fig_a": {"image_id": "fig_a", "page": 78}}
    monkeypatch.setattr(vs, "render_procedure_images", lambda *a, **k: [ImageInput(data=b"x")])

    cache: dict = {}
    first = vs.get_or_reconstruct(vision, _procedure(), figures, "x.pdf", cache=cache, cache_path=cache_file)
    assert len(first) == 1
    assert vision.calls == 1
    # second call hits the in-memory cache; no new vision call
    second = vs.get_or_reconstruct(vision, _procedure(), figures, "x.pdf", cache=cache, cache_path=cache_file)
    assert second == first
    assert vision.calls == 1
    # cache persisted to disk
    rows = [json.loads(line) for line in cache_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows and rows[0]["key"].startswith("m_fru_1070|")


def test_load_cache_round_trip(tmp_path: Path):
    cache_file = tmp_path / "vision_steps.jsonl"
    cache_file.write_text(
        json.dumps({"key": "k1", "steps": [{"text": "step"}]}) + "\n", encoding="utf-8"
    )
    loaded = vs.load_cache(cache_file)
    assert loaded["k1"] == [{"text": "step"}]
