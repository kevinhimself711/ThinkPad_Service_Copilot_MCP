import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def test_thinkpad_extract_hmm_cli_writes_summary_for_synthetic_pdf():
    work_dir = Path("data/extracted/test_m3_cli")
    pdf_dir = Path("data/manuals/test_m3_cli")
    output_dir = work_dir / "out"
    manifest_path = work_dir / "manifest.yaml"
    pdf_path = pdf_dir / "synthetic_hmm.pdf"

    shutil.rmtree(work_dir, ignore_errors=True)
    shutil.rmtree(pdf_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    try:
        _write_synthetic_pdf(pdf_path)
        manifest_path.write_text(
            yaml.safe_dump(
                {
                    "manuals": [
                        {
                            "manual_id": "thinkpad_synthetic_hmm",
                            "title": "Synthetic ThinkPad HMM",
                            "models": ["ThinkPad Synthetic"],
                            "generations": ["Gen 1"],
                            "machine_types": ["20ZZ"],
                            "source_type": "lenovo_official",
                            "source_url": "https://download.lenovo.com/pccbbs/mobiles_pdf/synthetic.pdf",
                            "local_pdf_path": str(pdf_path).replace("\\", "/"),
                            "spike_status": "planned",
                        }
                    ]
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "scripts/thinkpad_extract_hmm.py",
                "--manifest",
                str(manifest_path),
                "--output-dir",
                str(output_dir),
                "--max-pages",
                "1",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr + result.stdout
        summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
        assert summary["totals"]["manuals_succeeded"] == 1
        assert summary["totals"]["pages"] == 1
        assert (output_dir / "fru_procedures.jsonl").exists()
        assert (output_dir / "warnings.jsonl").exists()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(pdf_dir, ignore_errors=True)


def _write_synthetic_pdf(path: Path) -> None:
    import fitz  # type: ignore

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        """1010 Base cover assembly
Removal steps of the base cover assembly
Remove the screws.
DANGER: Disconnect the battery before service.
""",
    )
    doc.save(path)
    doc.close()
