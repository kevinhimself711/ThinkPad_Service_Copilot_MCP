#!/usr/bin/env python
"""Download official Lenovo HMM PDFs from a ThinkPad manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import yaml

from src.thinkpad.lenovo import DEFAULT_USER_AGENT
from src.thinkpad.manifest import ManualMetadata, load_manifest
from src.thinkpad.spike import compute_sha256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Lenovo HMM PDFs listed in a manifest.")
    parser.add_argument("--manifest", required=True, help="Manifest YAML to download.")
    parser.add_argument(
        "--output-dir",
        default="data/manuals",
        help="Directory for local PDF files. Must stay under data/manuals.",
    )
    parser.add_argument(
        "--update-manifest",
        help="Write a copy of the manifest with checksum and file size fields populated.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate URLs without writing PDFs.")
    return parser.parse_args()


def _validate_lenovo_pdf_url(url: str) -> None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not (host == "download.lenovo.com" or host.endswith(".lenovo.com")):
        raise ValueError(f"not an official Lenovo URL: {url}")
    if not parsed.path.lower().endswith(".pdf"):
        raise ValueError(f"not a PDF URL: {url}")


def _download(url: str, output_path: Path, expected_size: int | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for _attempt in range(1, 6):
        current_size = output_path.stat().st_size if output_path.exists() else 0
        if expected_size and current_size == expected_size:
            return
        if expected_size and current_size > expected_size:
            output_path.unlink()
            current_size = 0

        headers = {"User-Agent": DEFAULT_USER_AGENT}
        if expected_size and current_size > 0:
            headers["Range"] = f"bytes={current_size}-"

        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=180) as response:
                content_type = response.headers.get("content-type", "").lower()
                status = getattr(response, "status", None)
                if "pdf" not in content_type and "octet-stream" not in content_type:
                    raise ValueError(f"unexpected content-type {content_type!r} for {url}")

                resume = current_size > 0 and status == 206
                mode = "ab" if resume else "wb"
                with output_path.open(mode) as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)

            if expected_size is None or output_path.stat().st_size == expected_size:
                return
            last_error = ValueError(
                f"incomplete download for {url}: got {output_path.stat().st_size}, "
                f"expected {expected_size} bytes"
            )
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error


def _remote_content_length(url: str) -> int | None:
    request = Request(url, method="HEAD", headers={"User-Agent": DEFAULT_USER_AGENT})
    with urlopen(request, timeout=30) as response:
        content_length = response.headers.get("content-length")
    return int(content_length) if content_length else None


def _with_download_result(manual: ManualMetadata, path: Path) -> ManualMetadata:
    data = manual.to_dict()
    data["local_pdf_path"] = str(path).replace("\\", "/")
    data["checksum_sha256"] = compute_sha256(path)
    data["file_size_bytes"] = path.stat().st_size
    data["spike_status"] = "downloaded"
    return ManualMetadata.from_mapping(data)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    normalized_output_dir = output_dir.as_posix().rstrip("/")
    if normalized_output_dir != "data/manuals":
        raise SystemExit("--output-dir must be data/manuals for M1 copyright/data governance")

    manuals = load_manifest(args.manifest)
    downloaded: list[ManualMetadata] = []
    failures = 0

    for manual in manuals:
        try:
            _validate_lenovo_pdf_url(manual.source_url)
            file_name = Path(urlparse(manual.source_url).path).name
            output_path = output_dir / file_name
            expected_size = _remote_content_length(manual.source_url)
            if args.dry_run:
                print(f"[DRY-RUN] {manual.manual_id}: {manual.source_url} -> {output_path}")
                downloaded.append(manual)
                continue
            if output_path.exists() and output_path.stat().st_size == 0:
                print(f"[RETRY] {manual.manual_id}: replacing empty local file")
                output_path.unlink()
            if output_path.exists() and expected_size and output_path.stat().st_size > expected_size:
                print(f"[RETRY] {manual.manual_id}: replacing oversized local file")
                output_path.unlink()
            if output_path.exists() and expected_size and output_path.stat().st_size < expected_size:
                print(f"[RESUME] {manual.manual_id}: resuming incomplete local file")
            if not output_path.exists():
                print(f"[DOWNLOAD] {manual.manual_id}: {manual.source_url}")
                _download(manual.source_url, output_path, expected_size)
            elif expected_size and output_path.stat().st_size < expected_size:
                _download(manual.source_url, output_path, expected_size)
            else:
                print(f"[SKIP] {manual.manual_id}: already exists at {output_path}")
            result = _with_download_result(manual, output_path)
            print(f"[OK] {manual.manual_id}: sha256={result.checksum_sha256} bytes={result.file_size_bytes}")
            downloaded.append(result)
        except Exception as exc:
            failures += 1
            print(f"[FAIL] {manual.manual_id}: {type(exc).__name__}: {exc}")
            downloaded.append(manual)

    if args.update_manifest and not args.dry_run:
        output_path = Path(args.update_manifest)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"manuals": [manual.to_dict() for manual in downloaded]}
        output_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(f"Wrote updated manifest: {output_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
