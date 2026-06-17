"""Bounded M8.7 live smoke: qwen-vl removal-step reconstruction on image_only FRUs.

Read-only w.r.t. the repo (writes only the gitignored vision cache). Samples a
capped number of real component image_only procedures across manuals, calls
qwen-vl live, and reports reconstructed steps, spec-leak check, and latency.
Requires DASHSCOPE_API_KEY in the environment. Not a committed artifact.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.core.settings import load_settings  # noqa: E402
from src.libs.llm.llm_factory import LLMFactory  # noqa: E402
from src.thinkpad import vision_steps as vs  # noqa: E402
from src.thinkpad.manifest import load_manifest  # noqa: E402

_DIAGNOSTIC = ("invalid", "uuid", "configuration", "error", "failure")
_LEAK = vs._SPEC_LEAK_RE
_CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 10


def main() -> int:
    settings = load_settings("config/settings.yaml")
    vision = LLMFactory.create_vision_llm(settings)
    manuals = {m.manual_id: m.local_pdf_path for m in load_manifest("data/manifests/manuals_manifest.yaml")}
    figures = {}
    for line in Path("data/extracted/m3/figures.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            f = json.loads(line)
            if f.get("image_id"):
                figures[str(f["image_id"])] = f
    procs = [json.loads(x) for x in Path("data/extracted/m3/fru_procedures.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

    sample = []
    seen = set()
    for p in procs:
        if p.get("presentation_type") != "image_only" or not p.get("related_image_ids"):
            continue
        name = (p.get("fru_name") or "").lower()
        if any(t in name for t in _DIAGNOSTIC):
            continue
        if len(p["related_image_ids"]) > 4:  # skip giant/odd image sets
            continue
        key = (p["manual_id"], name[:18])
        if key in seen:
            continue
        seen.add(key)
        sample.append(p)
        if len(sample) >= _CAP:
            break

    print(f"sampled {len(sample)} image_only procedures; model={vision.model}\n")
    latencies = []
    leaks = 0
    empty = 0
    for p in sample:
        pdf = manuals.get(p["manual_id"])
        t0 = time.time()
        try:
            steps = vs.get_or_reconstruct(vision, p, figures, pdf, cache={})
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {p['fru_id']} {p['fru_name'][:30]}: {exc}")
            continue
        dt = time.time() - t0
        latencies.append(dt)
        if not steps:
            empty += 1
        leaked = [s for s in steps if _LEAK.search(s["text"])]
        leaks += len(leaked)
        print(f"=== {p['manual_id'][:24]} {p['fru_id']} {p['fru_name'][:28]} ({dt:.1f}s, {len(steps)} steps) ===")
        for s in steps:
            print(f"   {s['step_index']}. {s['text'][:90]}")
        if leaked:
            print(f"   !! SPEC LEAK in {len(leaked)} step(s)")

    if latencies:
        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95) - 1] if len(latencies) > 1 else latencies[0]
        print(f"\nlatency: mean={sum(latencies)/len(latencies):.1f}s p95={p95:.1f}s n={len(latencies)}")
    print(f"empty_reconstructions={empty}/{len(sample)}  spec_leaks={leaks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
