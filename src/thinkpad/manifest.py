"""Manifest contracts for local ThinkPad HMM corpus management.

The manifest stores official source metadata and local-only PDF paths. It is
safe to commit example manifests that contain Lenovo source URLs, but real
checksums and downloaded files should stay under ignored data directories.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


class ManifestError(ValueError):
    """Raised when a ThinkPad manual manifest is invalid."""


@dataclass(frozen=True)
class ManualMetadata:
    """Manual-level metadata used by the M1 spike and later ingestion stages."""

    manual_id: str
    title: str
    models: list[str]
    generations: list[str]
    machine_types: list[str]
    source_type: str
    source_url: str
    local_pdf_path: str
    document_type: str = "hmm"
    language: str = "en"
    product_page_url: str | None = None
    year: int | None = None
    edition: str | None = None
    page_count: int | None = None
    checksum_sha256: str | None = None
    file_size_bytes: int | None = None
    product_guids: list[str] = field(default_factory=list)
    spike_status: str = "planned"
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ManualMetadata:
        """Build a validated metadata object from a YAML mapping."""

        if not isinstance(data, dict):
            raise ManifestError(f"manual entry must be a mapping, got {type(data).__name__}")

        required_fields = [
            "manual_id",
            "title",
            "models",
            "generations",
            "machine_types",
            "source_type",
            "source_url",
            "local_pdf_path",
        ]
        missing = [field_name for field_name in required_fields if field_name not in data]
        if missing:
            raise ManifestError(f"manual entry is missing required fields: {', '.join(missing)}")

        normalized = dict(data)
        for list_field in ("models", "generations", "machine_types", "product_guids", "notes"):
            value = normalized.get(list_field, [])
            if value is None:
                value = []
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ManifestError(f"{list_field} must be a list of strings")
            normalized[list_field] = value

        try:
            manual = cls(**normalized)
        except TypeError as exc:
            raise ManifestError(str(exc)) from exc

        manual.validate()
        return manual

    def validate(self) -> None:
        """Validate domain and data-governance invariants."""

        if not self.manual_id.strip():
            raise ManifestError("manual_id cannot be empty")
        if self.document_type != "hmm":
            raise ManifestError(f"document_type must be 'hmm', got {self.document_type!r}")
        if self.source_type != "lenovo_official":
            raise ManifestError("ThinkPad manifests only allow source_type='lenovo_official'")
        if not self.models:
            raise ManifestError(f"{self.manual_id}: models cannot be empty")
        if not self.generations:
            raise ManifestError(f"{self.manual_id}: generations cannot be empty")
        if not self.machine_types:
            raise ManifestError(f"{self.manual_id}: machine_types cannot be empty")
        if self.spike_status not in {"planned", "discovered", "downloaded", "validated"}:
            raise ManifestError(
                f"{self.manual_id}: spike_status must be one of planned, discovered, downloaded, validated"
            )

        source_host = urlparse(self.source_url).netloc.lower()
        if not (source_host == "download.lenovo.com" or source_host.endswith(".lenovo.com")):
            raise ManifestError(f"{self.manual_id}: source_url must be an official Lenovo URL")

        if self.product_page_url:
            product_host = urlparse(self.product_page_url).netloc.lower()
            if not (product_host == "pcsupport.lenovo.com" or product_host.endswith(".lenovo.com")):
                raise ManifestError(f"{self.manual_id}: product_page_url must be an official Lenovo URL")

        path = Path(self.local_pdf_path)
        if path.is_absolute():
            raise ManifestError(f"{self.manual_id}: local_pdf_path must be repo-relative")
        if not str(path).replace("\\", "/").startswith("data/manuals/"):
            raise ManifestError(f"{self.manual_id}: local_pdf_path must stay under data/manuals/")

        if self.checksum_sha256 is not None:
            checksum = self.checksum_sha256.lower()
            if len(checksum) != 64 or any(ch not in "0123456789abcdef" for ch in checksum):
                raise ManifestError(f"{self.manual_id}: checksum_sha256 must be a 64-char hex digest")
        if self.file_size_bytes is not None and self.file_size_bytes <= 0:
            raise ManifestError(f"{self.manual_id}: file_size_bytes must be positive when provided")
        if self.page_count is not None and self.page_count <= 0:
            raise ManifestError(f"{self.manual_id}: page_count must be positive when provided")

        if self.spike_status in {"downloaded", "validated"}:
            if self.checksum_sha256 is None:
                raise ManifestError(f"{self.manual_id}: downloaded/validated manuals require checksum_sha256")
            if self.file_size_bytes is None:
                raise ManifestError(f"{self.manual_id}: downloaded/validated manuals require file_size_bytes")
            if not self.local_pdf_path.strip():
                raise ManifestError(f"{self.manual_id}: downloaded/validated manuals require local_pdf_path")
        if self.spike_status == "validated" and self.page_count is None:
            raise ManifestError(f"{self.manual_id}: validated manuals require page_count")

    def to_dict(self) -> dict[str, Any]:
        """Return a YAML/JSON serializable representation."""

        return asdict(self)


def load_manifest(path: str | Path) -> list[ManualMetadata]:
    """Load and validate a ThinkPad HMM manifest YAML file."""

    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if isinstance(raw, dict) and "manuals" in raw:
        raw_manuals = raw["manuals"]
    else:
        raw_manuals = raw

    if not isinstance(raw_manuals, list):
        raise ManifestError("manifest must be a list or a mapping with a 'manuals' list")

    manuals = [ManualMetadata.from_mapping(entry) for entry in raw_manuals]
    manual_ids = [manual.manual_id for manual in manuals]
    duplicates = sorted({manual_id for manual_id in manual_ids if manual_ids.count(manual_id) > 1})
    if duplicates:
        raise ManifestError(f"duplicate manual_id values: {', '.join(duplicates)}")

    return manuals


def dump_manifest(manuals: list[ManualMetadata], path: str | Path) -> None:
    """Write a manifest YAML file using the ThinkPad manual metadata schema."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"manuals": [manual.to_dict() for manual in manuals]}
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
