from pathlib import Path

from src.thinkpad.manifest import load_manifest
from src.thinkpad.model_resolver import resolve_thinkpad_model


def _manuals():
    return load_manifest(Path("tests/fixtures/thinkpad_mini_manifest.yaml"))


def test_resolver_prefers_exact_machine_type():
    resolution = resolve_thinkpad_model("battery replacement for 21CB", _manuals())

    assert resolution.clarification_needed is False
    assert resolution.reason == "exact_machine_type_match"
    assert resolution.best_candidate is not None
    assert resolution.best_candidate.manual_id == "thinkpad_x1_carbon_gen10_x1_yoga_gen7_hmm"
    assert "21CB" in resolution.machine_type_candidates


def test_resolver_handles_exact_model_generation():
    resolution = resolve_thinkpad_model("X1 Carbon Gen 9 battery removal", _manuals())

    assert resolution.clarification_needed is False
    assert resolution.best_candidate is not None
    assert resolution.best_candidate.canonical_model == "ThinkPad X1 Carbon Gen 9"
    assert resolution.best_candidate.manual_id == "thinkpad_x1_carbon_gen9_x1_yoga_gen6_hmm"


def test_resolver_handles_compact_generation_alias():
    resolution = resolve_thinkpad_model("T14 Gen2 system board", _manuals())

    assert resolution.clarification_needed is False
    assert resolution.best_candidate is not None
    assert resolution.best_candidate.canonical_model == "ThinkPad T14 Gen 2"


def test_resolver_handles_ordinal_generation_alias():
    resolution = resolve_thinkpad_model("E15 second gen error code 0271", _manuals())

    assert resolution.clarification_needed is False
    assert resolution.best_candidate is not None
    assert resolution.best_candidate.canonical_model == "ThinkPad E15 Gen 2"
    assert resolution.best_candidate.manual_id == "thinkpad_e14_gen2_e15_gen2_hmm"


def test_resolver_requires_clarification_for_generationless_family():
    resolution = resolve_thinkpad_model("X1 Carbon battery removal", _manuals())

    assert resolution.clarification_needed is True
    assert resolution.reason == "generation_required"
    assert {candidate.canonical_model for candidate in resolution.candidates} == {
        "ThinkPad X1 Carbon Gen 9",
        "ThinkPad X1 Carbon Gen 10",
    }


def test_resolver_distinguishes_explicit_unsupported_generation():
    resolution = resolve_thinkpad_model("X1 Carbon Gen 11 battery removal", _manuals())

    assert resolution.clarification_needed is True
    assert resolution.reason == "unsupported_generation"
    assert {candidate.canonical_model for candidate in resolution.candidates} == {
        "ThinkPad X1 Carbon Gen 9",
        "ThinkPad X1 Carbon Gen 10",
    }
    assert any(
        "unsupported_generation" in candidate.matched_on
        for candidate in resolution.candidates
    )


def test_resolver_ignores_negated_generation_interference():
    resolution = resolve_thinkpad_model("X1 Carbon Gen 10 battery removal, not Gen 9", _manuals())

    assert resolution.clarification_needed is False
    assert resolution.reason == "model_generation_match"
    assert resolution.best_candidate is not None
    assert resolution.best_candidate.canonical_model == "ThinkPad X1 Carbon Gen 10"


def test_resolver_returns_unsupported_for_unknown_model():
    resolution = resolve_thinkpad_model("ThinkPad Z13 battery", _manuals())

    assert resolution.clarification_needed is True
    assert resolution.reason == "unsupported_model"
    assert resolution.candidates == []
