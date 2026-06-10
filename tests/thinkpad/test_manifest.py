from pathlib import Path

import pytest
import yaml

from src.thinkpad.manifest import ManifestError, ManualMetadata, load_manifest


def _valid_payload(**overrides):
    payload = {
        "manual_id": "thinkpad_t14_gen2_p14s_gen2_hmm",
        "title": "ThinkPad P14s Gen 2, T14 Gen 2 Hardware Maintenance Manual",
        "models": ["ThinkPad T14 Gen 2", "ThinkPad P14s Gen 2"],
        "generations": ["Gen 2"],
        "machine_types": ["20W0", "20W1"],
        "source_type": "lenovo_official",
        "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/t14_gen2_p14s_gen2_hmm_en.pdf",
        "product_page_url": (
            "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/"
            "thinkpad-t-series-laptops/thinkpad-t14-gen-2-type-20w0-20w1/20w1/"
            "selfrepair/removalsreplacements"
        ),
        "local_pdf_path": "data/manuals/t14_gen2_p14s_gen2_hmm_en.pdf",
        "page_count": 133,
        "spike_status": "planned",
    }
    payload.update(overrides)
    return payload


def test_load_manifest_accepts_official_lenovo_hmm_fixture():
    manuals = load_manifest(Path("tests/fixtures/thinkpad_mini_manifest.yaml"))

    assert len(manuals) == 5
    assert manuals[0].manual_id == "thinkpad_t14_gen2_p14s_gen2_hmm"
    assert manuals[0].source_type == "lenovo_official"
    assert manuals[0].local_pdf_path.startswith("data/manuals/")
    assert manuals[0].page_count == 133


def test_load_manifest_accepts_committed_m1_example_manifest():
    manuals = load_manifest(Path("config/manuals_manifest.example.yaml"))

    assert len(manuals) == 8
    assert manuals[-1].manual_id == "thinkpad_p1_gen4_x1_extreme_gen4_hmm"
    assert sum(manual.page_count or 0 for manual in manuals) == 877


def test_manifest_rejects_non_lenovo_source_url():
    payload = _valid_payload(source_url="https://example.com/manual.pdf")

    with pytest.raises(ManifestError, match="official Lenovo URL"):
        ManualMetadata.from_mapping(payload)


def test_manifest_rejects_paths_outside_data_manuals():
    payload = _valid_payload(local_pdf_path="docs/manual.pdf")

    with pytest.raises(ManifestError, match="data/manuals"):
        ManualMetadata.from_mapping(payload)


def test_manifest_rejects_absolute_local_paths():
    payload = _valid_payload(local_pdf_path="D:/ThinkPad_Service_Copilot_MCP/data/manuals/manual.pdf")

    with pytest.raises(ManifestError, match="repo-relative"):
        ManualMetadata.from_mapping(payload)


def test_manifest_rejects_invalid_checksum():
    payload = _valid_payload(checksum_sha256="not-a-sha")

    with pytest.raises(ManifestError, match="64-char hex"):
        ManualMetadata.from_mapping(payload)


def test_manifest_rejects_duplicate_manual_ids():
    manifest_path = Path("data/extracted/test_duplicate_manifest.yaml")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump({"manuals": [_valid_payload(), _valid_payload()]}, sort_keys=False),
        encoding="utf-8",
    )

    try:
        with pytest.raises(ManifestError, match="duplicate manual_id"):
            load_manifest(manifest_path)
    finally:
        manifest_path.unlink(missing_ok=True)


def test_downloaded_manifest_requires_checksum_and_size():
    payload = _valid_payload(spike_status="downloaded", checksum_sha256=None, file_size_bytes=None)

    with pytest.raises(ManifestError, match="checksum_sha256"):
        ManualMetadata.from_mapping(payload)


def test_validated_manifest_requires_page_count():
    payload = _valid_payload(
        spike_status="validated",
        checksum_sha256="a" * 64,
        file_size_bytes=65810405,
        page_count=None,
    )

    with pytest.raises(ManifestError, match="page_count"):
        ManualMetadata.from_mapping(payload)


def test_manifest_accepts_validated_local_record_metadata():
    manual = ManualMetadata.from_mapping(
        _valid_payload(
            spike_status="validated",
            checksum_sha256="91f8c030f7b4d23a7b0ede4c26b3d3561bb69a2b2a5b647a9a2e466e39aace15",
            file_size_bytes=65810405,
            product_guids=["GUID-A", "PARENT-GUID-B"],
        )
    )

    assert manual.spike_status == "validated"
    assert manual.product_guids == ["GUID-A", "PARENT-GUID-B"]
