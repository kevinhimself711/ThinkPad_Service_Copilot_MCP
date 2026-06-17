"""Larger-scale M8.7 live evaluation: vision step reconstruction + figure correctness.

For every real-component image_only FRU across all 8 manuals, this:
  (1) reconstructs removal steps via qwen-vl (success / spec-leak / latency), and
  (2) renders the returned figure and asks qwen-vl to NAME the component, then
      checks that name matches the queried FRU ("did we return the correct image").

Read-only w.r.t. the repo (writes only the gitignored vision cache + a local
ignored JSONL report). Requires DASHSCOPE_API_KEY in the env. Not committed.
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
from src.libs.llm.llm_factory import LLMFactory  # noqa: E402
from src.thinkpad import vision_steps as vs  # noqa: E402
from src.thinkpad.manifest import load_manifest  # noqa: E402

_DIAGNOSTIC = ("invalid", "uuid", "configuration", "error", "failure")
_STOPWORDS = {"the", "a", "an", "for", "assembly", "card", "module", "and", "of", "with", "selected", "models", "only"}
_LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # 0 = all


def _tokens(name: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9.]+", name.lower()) if t not in _STOPWORDS and len(t) > 1}


def _name_matches(expected: str, seen: str) -> bool:
    """Lenient overlap: the figure is 'correct' if the model's component name
    shares a meaningful content token with the FRU name (e.g. 'speaker')."""
    exp, got = _tokens(expected), _tokens(seen)
    if not exp:
        return False
    # core nouns that anchor identity
    return bool(exp & got)


def main() -> int:
    settings = load_settings("config/settings.yaml")
    vision = LLMFactory.create_vision_llm(settings)
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
        and len(p["related_image_ids"]) <= 4
    ]
    if _LIMIT:
        sample = sample[:_LIMIT]

    name_prompt = (
        "This is a service diagram from a laptop hardware manual. In 6 words or fewer, "
        "name the single component this exploded-view illustrates being removed. "
        "Answer with the component name only."
    )

    recon_lat, name_lat = [], []
    empty = leaks = fig_correct = fig_total = 0
    rows = []
    for i, p in enumerate(sample, 1):
        pdf = manuals.get(p["manual_id"])
        imgs = vs.render_procedure_images(p, figs, pdf)
        # (1) reconstruction
        t0 = time.time()
        steps = vs.reconstruct_steps(vision, imgs, p)
        recon_lat.append(time.time() - t0)
        if not steps:
            empty += 1
        leaked = sum(1 for s in steps if vs._SPEC_LEAK_RE.search(s["text"]))
        leaks += leaked
        # (2) figure correctness
        seen = ""
        ok = None
        if imgs:
            fig_total += 1
            t1 = time.time()
            try:
                seen = (vision.chat_with_image(name_prompt, imgs[0]).content or "").strip().replace("\n", " ")[:50]
                ok = _name_matches(p["fru_name"], seen)
                if ok:
                    fig_correct += 1
            except Exception as exc:  # noqa: BLE001
                seen = f"ERROR {exc}"
            name_lat.append(time.time() - t1)
        rows.append({"manual": p["manual_id"], "fru_id": p["fru_id"], "fru_name": p["fru_name"],
                     "steps": len(steps), "leaks": leaked, "fig_seen": seen, "fig_ok": ok})
        if i % 20 == 0:
            print(f"  ...{i}/{len(sample)} done")

    def p95(xs):
        xs = sorted(xs)
        return xs[int(len(xs) * 0.95) - 1] if len(xs) > 1 else (xs[0] if xs else 0)

    print(f"\n=== M8.7 larger live eval: {len(sample)} image_only FRUs (8 manuals) ===")
    print(f"reconstruction: non-empty={len(sample)-empty}/{len(sample)} ({100*(len(sample)-empty)//max(len(sample),1)}%)  spec_leaks={leaks}")
    print(f"figure correctness (qwen-vl names returned image == queried FRU): {fig_correct}/{fig_total} ({100*fig_correct//max(fig_total,1)}%)")
    print(f"latency reconstruct: mean={sum(recon_lat)/max(len(recon_lat),1):.1f}s p95={p95(recon_lat):.1f}s")
    print(f"latency name-check: mean={sum(name_lat)/max(len(name_lat),1):.1f}s p95={p95(name_lat):.1f}s")
    print("\n--- figure MISMATCHES (returned image may not match FRU) ---")
    for r in rows:
        if r["fig_ok"] is False:
            print(f"  {r['manual'][:22]} {r['fru_id']} expected='{r['fru_name'][:26]}' seen='{r['fig_seen']}'")

    out = Path("data/eval/m8_7_vision_live_report.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"\nper-FRU report (gitignored): {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
