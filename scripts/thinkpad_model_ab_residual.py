"""M8.11 model A/B: is the residual figure-match failure RECOGNITION or SELECTION?

For each residual image_only FRU (the figures that M8.10 returned but qwen-vl
named as a NEIGHBOR component), render the EXACT image get_fru_procedure would
return (identical bytes), then ask each candidate vision model to name the
component. Identical image, different models -> isolates model capability.

Interpretation:
  - If a STRONGER model also names the neighbor -> SELECTION problem (the image
    we pick is wrong / the small part is not the visual subject). Model swap
    won't help; M8.11 text-anchor selection is the fix.
  - If a stronger model names the queried FRU correctly -> RECOGNITION problem.
    The model swap helps directly.

Read-only w.r.t. the repo (writes only a gitignored JSONL report). Requires
DASHSCOPE_API_KEY. Candidate model IDs are passed on argv so we never hardcode
guesses; each is probed once and skipped if the API rejects it.

Usage:
  DASHSCOPE_API_KEY=*** python scripts/thinkpad_model_ab_residual.py \
      qwen-vl-max qwen3-vl-plus qwen3.7-plus
"""

from __future__ import annotations

import json
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

_STOPWORDS = {"the", "a", "an", "for", "assembly", "card", "module", "and", "of",
              "with", "selected", "models", "only", "gen"}
_NAME_PROMPT = (
    "This is a service diagram from a laptop hardware manual. In 6 words or fewer, "
    "name the single component this exploded-view illustrates being removed. "
    "Answer with the component name only."
)


def _tokens(name: str) -> set[str]:
    name = re.sub(r"\(.*?\)", " ", name.lower())
    name = re.sub(r"\bgen\s*\d+\b", " ", name)
    return {t for t in re.findall(r"[a-z0-9.]+", name) if t not in _STOPWORDS and len(t) > 1}


def _name_matches(expected: str, seen: str) -> bool:
    exp, got = _tokens(expected), _tokens(seen)
    return bool(exp and (exp & got))


def _make_model(settings, model_id: str) -> DashScopeVisionLLM:
    llm = DashScopeVisionLLM(settings)
    llm.model = model_id  # override per-candidate; provider is OpenAI-compatible
    return llm


def _probe(llm: DashScopeVisionLLM, img) -> tuple[bool, str]:
    """One tiny call to confirm the model id is callable and accepts an image."""
    try:
        out = llm.chat_with_image("Reply with the single word: ok", img)
        return True, (out.content or "").strip()[:40]
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {str(exc)[:80]}"


def main() -> int:
    model_ids = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not model_ids:
        print("usage: thinkpad_model_ab_residual.py <model_id> [<model_id> ...]")
        return 2

    settings = load_settings("config/settings.yaml")
    manuals = {m.manual_id: m.local_pdf_path for m in load_manifest("data/manifests/manuals_manifest.yaml")}

    figs = {}
    for line in Path("data/extracted/m3/figures.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            f = json.loads(line)
            if f.get("image_id"):
                figs[str(f["image_id"])] = f
    procs = {(p["manual_id"], p["fru_id"]): p
             for p in (json.loads(x) for x in Path("data/extracted/m3/fru_procedures.jsonl").read_text(encoding="utf-8").splitlines() if x.strip())}

    # Residual failures: prefer the on-disk M8.10 residual eval; each row has
    # manual + fru_id + fig_ok. We re-render and re-ask, so stale 'seen' is fine.
    residual_path = Path("data/eval/m8_10_vision_live_m8_9_failures_v2.jsonl")
    residual_rows = [json.loads(x) for x in residual_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    targets = [(r["manual"], r["fru_id"], r["fru_name"]) for r in residual_rows if r.get("fig_ok") is False]
    # de-dup (manual, fru_id)
    seen_keys = set()
    uniq = []
    for t in targets:
        k = (t[0], t[1])
        if k not in seen_keys:
            seen_keys.add(k)
            uniq.append(t)
    targets = uniq
    print(f"residual targets (fig_ok==False, deduped): {len(targets)}")

    # Render each target's primary image ONCE (identical bytes for all models).
    rendered = []
    for mid, fru_id, fru_name in targets:
        proc = procs.get((mid, fru_id))
        if not proc:
            print(f"  skip {mid} {fru_id}: not in procedures")
            continue
        imgs = vs.render_procedure_images(proc, figs, manuals.get(mid))
        if not imgs:
            print(f"  skip {mid} {fru_id}: no rendered image")
            continue
        rendered.append((mid, fru_id, fru_name, imgs[0]))
    print(f"rendered residual images: {len(rendered)}\n")

    if not rendered:
        print("nothing to test")
        return 1

    # Probe each model id with the first rendered image; drop dead ids.
    live_models = {}
    for mid in model_ids:
        llm = _make_model(settings, mid)
        ok, msg = _probe(llm, rendered[0][3])
        print(f"probe {mid:18} -> {'OK' if ok else 'DEAD'}  {msg}")
        if ok:
            live_models[mid] = llm
    print()
    if not live_models:
        print("no callable models")
        return 1

    rows = []
    tallies = {mid: 0 for mid in live_models}
    lat = {mid: [] for mid in live_models}
    for mid, fru_id, fru_name, img in rendered:
        rec = {"manual": mid, "fru_id": fru_id, "fru_name": fru_name, "by_model": {}}
        for model_id, llm in live_models.items():
            t0 = time.time()
            try:
                seen = (llm.chat_with_image(_NAME_PROMPT, img).content or "").strip().replace("\n", " ")[:50]
                ok = _name_matches(fru_name, seen)
            except Exception as exc:  # noqa: BLE001
                seen, ok = f"ERROR {type(exc).__name__}", False
            lat[model_id].append(time.time() - t0)
            if ok:
                tallies[model_id] += 1
            rec["by_model"][model_id] = {"seen": seen, "ok": ok}
        rows.append(rec)
        cells = "  ".join(f"{m}:{'OK ' if rec['by_model'][m]['ok'] else 'x  '}{rec['by_model'][m]['seen'][:22]}" for m in live_models)
        print(f"  {mid[:18]:18} {fru_id:5} {fru_name[:24]:24} | {cells}")

    n = len(rendered)
    print(f"\n=== M8.11 model A/B on {n} residual figures (identical images) ===")
    for model_id in live_models:
        xs = sorted(lat[model_id])
        p95 = xs[int(len(xs) * 0.95) - 1] if len(xs) > 1 else (xs[0] if xs else 0)
        print(f"  {model_id:18} correctly-named {tallies[model_id]}/{n} ({100*tallies[model_id]//max(n,1)}%)  lat mean={sum(lat[model_id])/max(len(lat[model_id]),1):.1f}s p95={p95:.1f}s")
    print("\nReading: if the strongest model's count is still low, the residual is a")
    print("SELECTION problem (wrong image shown), not a recognition/model-capacity one.")

    out = Path("data/eval/m8_11_model_ab_residual.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"\nper-figure report (gitignored): {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
