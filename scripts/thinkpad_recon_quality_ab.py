"""M8.11 reconstruction-quality A/B: does a stronger VLM produce better removal steps?

figure-match measures which image we SELECT, so it is (by design) insensitive to
the reconstruction model. The place a stronger VLM pays off is the QUALITY of the
reconstructed removal steps. This script measures that directly.

For every real-component image_only FRU (same M8.9/M8.10 population + selection):
  1. render the SAME primary diagram once (M8.10 selection, unchanged);
  2. reconstruct steps with BOTH candidate models (e.g. qwen-vl-max vs qwen3-vl-plus);
  3. a fixed third-party JUDGE model does an anonymized, side-randomized pairwise
     comparison ("which step list better describes the removal in THIS image?").

To control judge self-preference bias, run the judge with each candidate model id
and report both judgements; a result is only "robust" when both judges agree.

Objective co-metrics (no judge): step count, spec-leak rate, empty rate, latency.

Read-only w.r.t. the repo (writes only a gitignored JSONL). Requires
DASHSCOPE_API_KEY. Candidate + judge model ids are passed on argv.

Usage:
  DASHSCOPE_API_KEY=*** python scripts/thinkpad_recon_quality_ab.py \
      --model-a qwen-vl-max --model-b qwen3-vl-plus \
      --judges qwen-vl-max,qwen3-vl-plus \
      --output data/eval/m8_11_recon_quality.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.core.settings import load_settings  # noqa: E402
from src.libs.llm.dashscope_vision_llm import DashScopeVisionLLM  # noqa: E402
from src.thinkpad import vision_steps as vs  # noqa: E402
from src.thinkpad.manifest import load_manifest  # noqa: E402

_DIAGNOSTIC = ("invalid", "uuid", "configuration", "error", "failure")
_CROP_KINDS = {"region_crop", "region_crop_precise", "region_crop_anchored"}

_JUDGE_PROMPT = (
    "You are auditing two AI-generated removal-step lists for a laptop service "
    "diagram (shown). Each list should describe, in order, the physical removal "
    "motions a technician performs for the named component. Judge ONLY which list "
    "more accurately and completely describes the removal actually depicted in the "
    "image. Ignore wording style. Do NOT reward mentions of screw counts/torque/FRU "
    "numbers (those are not the image's job).\n\n"
    "Component: {component}\n\n"
    "List A:\n{a}\n\nList B:\n{b}\n\n"
    "Answer with exactly one token: A, B, or TIE."
)


def _make_model(settings, model_id: str) -> DashScopeVisionLLM:
    llm = DashScopeVisionLLM(settings)
    llm.model = model_id
    return llm


def _baseline_image_count(procedure: dict, figures: dict) -> int:
    return sum(
        1
        for i in (procedure.get("related_image_ids") or [])
        if (figures.get(str(i)) or {}).get("figure_kind") not in _CROP_KINDS
    )


def _steps_text(steps: list[dict]) -> str:
    return "\n".join(f"{s['step_index']}. {s['text']}" for s in steps) or "(no steps)"


def _verdict(judge, image, component: str, a_text: str, b_text: str) -> str:
    prompt = _JUDGE_PROMPT.format(component=component, a=a_text, b=b_text)
    try:
        out = (judge.chat_with_image(prompt, image).content or "").strip().upper()
    except Exception as exc:  # noqa: BLE001
        return f"ERR:{type(exc).__name__}"
    if out.startswith("A"):
        return "A"
    if out.startswith("B"):
        return "B"
    return "TIE"


def main() -> int:
    parser = argparse.ArgumentParser(description="M8.11 reconstruction-quality A/B.")
    parser.add_argument("--model-a", default="qwen-vl-max")
    parser.add_argument("--model-b", default="qwen3-vl-plus")
    parser.add_argument("--judges", default="qwen-vl-max,qwen3-vl-plus")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", default="data/eval/m8_11_recon_quality.jsonl")
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()

    random.seed(args.seed)
    settings = load_settings("config/settings.yaml")
    manuals = {m.manual_id: m.local_pdf_path for m in load_manifest("data/manifests/manuals_manifest.yaml")}
    figs = {}
    for line in Path("data/extracted/m3/figures.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            f = json.loads(line)
            if f.get("image_id"):
                figs[str(f["image_id"])] = f
    procs = [json.loads(x) for x in Path("data/extracted/m3/fru_procedures.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

    sample = [
        p for p in procs
        if p.get("presentation_type") == "image_only" and p.get("related_image_ids")
        and not any(t in (p.get("fru_name") or "").lower() for t in _DIAGNOSTIC)
        and _baseline_image_count(p, figs) <= 4
    ]
    if args.limit:
        sample = sample[: args.limit]

    model_a = _make_model(settings, args.model_a)
    model_b = _make_model(settings, args.model_b)
    judge_ids = [j.strip() for j in args.judges.split(",") if j.strip()]
    judges = {j: _make_model(settings, j) for j in judge_ids}

    wins = {jid: {"A": 0, "B": 0, "TIE": 0, "ERR": 0} for jid in judges}
    a_steps_tot = b_steps_tot = a_empty = b_empty = a_leak = b_leak = 0
    lat_a, lat_b = [], []
    rows = []
    print(f"sample: {len(sample)}  A={args.model_a}  B={args.model_b}  judges={judge_ids}")
    for i, p in enumerate(sample, 1):
        pdf = manuals.get(p["manual_id"])
        imgs = vs.render_procedure_images(p, figs, pdf)  # M8.10 selection, unchanged
        if not imgs:
            continue
        img = imgs[0]
        t0 = time.time(); steps_a = vs.reconstruct_steps(model_a, [img], p); lat_a.append(time.time() - t0)
        t1 = time.time(); steps_b = vs.reconstruct_steps(model_b, [img], p); lat_b.append(time.time() - t1)
        a_steps_tot += len(steps_a); b_steps_tot += len(steps_b)
        a_empty += not steps_a; b_empty += not steps_b
        la = sum(1 for s in steps_a if vs._SPEC_LEAK_RE.search(s["text"]))
        lb = sum(1 for s in steps_b if vs._SPEC_LEAK_RE.search(s["text"]))
        a_leak += la; b_leak += lb
        a_txt, b_txt = _steps_text(steps_a), _steps_text(steps_b)

        # anonymize + randomize side per FRU to remove position bias
        flip = random.random() < 0.5
        left, right = (b_txt, a_txt) if flip else (a_txt, b_txt)  # "List A"=left
        per_judge = {}
        for jid, judge in judges.items():
            v = _verdict(judge, img, p["fru_name"], left, right)
            # map back to model identity
            if v in ("A", "B"):
                winner_is_b = (v == "A") if flip else (v == "B")
                outcome = "B" if winner_is_b else "A"
            elif v == "TIE":
                outcome = "TIE"
            else:
                outcome = "ERR"
            wins[jid][outcome if outcome in wins[jid] else "ERR"] += 1
            per_judge[jid] = {"raw": v, "outcome": outcome}
        rows.append({
            "manual": p["manual_id"], "fru_id": p["fru_id"], "fru_name": p["fru_name"],
            "a_steps": len(steps_a), "b_steps": len(steps_b),
            "a_leak": la, "b_leak": lb, "flip": flip,
            "judges": per_judge,
            "a_text": a_txt, "b_text": b_txt,
        })
        if i % 20 == 0:
            print(f"  ...{i}/{len(sample)} done")

    n = len(rows)
    print(f"\n=== M8.11 reconstruction-quality A/B: n={n} image_only FRUs ===")
    print(f"A={args.model_a}  B={args.model_b}")
    print(f"objective: A_steps_avg={a_steps_tot/max(n,1):.1f} B_steps_avg={b_steps_tot/max(n,1):.1f}  "
          f"A_empty={a_empty} B_empty={b_empty}  A_leaks={a_leak} B_leaks={b_leak}")
    print(f"latency: A mean={sum(lat_a)/max(len(lat_a),1):.1f}s  B mean={sum(lat_b)/max(len(lat_b),1):.1f}s")
    for jid, w in wins.items():
        decided = w["A"] + w["B"]
        br = 100 * w["B"] / max(decided, 1)
        print(f"judge={jid:16} B-wins={w['B']} A-wins={w['A']} TIE={w['TIE']} ERR={w['ERR']}  -> B win-rate(decided)={br:.0f}%")
    # robust agreement: both judges pick B
    if len(judges) >= 2:
        jids = list(judges)
        both_b = sum(1 for r in rows if all(r["judges"][j]["outcome"] == "B" for j in jids))
        both_a = sum(1 for r in rows if all(r["judges"][j]["outcome"] == "A" for j in jids))
        print(f"robust (all judges agree): B better on {both_b}, A better on {both_a}, rest mixed/tie")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"\nper-FRU report (gitignored): {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
