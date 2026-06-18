"""Larger-scale M8.7 live evaluation: vision step reconstruction + figure correctness.

For every real-component image_only FRU across all 8 manuals, this:
  (1) reconstructs removal steps via qwen-vl (success / spec-leak / latency), and
  (2) renders the returned figure and asks qwen-vl to NAME the component, then
      checks that name matches the queried FRU ("did we return the correct image").

Read-only w.r.t. the repo (writes only the gitignored vision cache + a local
ignored JSONL report). Requires DASHSCOPE_API_KEY in the env. Not committed.
"""

from __future__ import annotations

import argparse
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live qwen-vl eval for ThinkPad image-only procedure diagrams.")
    parser.add_argument("legacy_limit", nargs="?", type=int, help="Backward-compatible positional limit.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum cases to run. 0 means all.")
    parser.add_argument(
        "--target",
        choices=["all", "previous-failures", "m8-9-failures", "recovered-regions"],
        default="all",
        help="Optional targeted population for M8.9 residual/no-image checks.",
    )
    parser.add_argument(
        "--previous-report",
        default="data/eval/m8_7_vision_live_report.jsonl",
        help="Prior live report used for --target previous-failures.",
    )
    parser.add_argument(
        "--output",
        default="data/eval/m8_7_vision_live_report.jsonl",
        help="Ignored JSONL output path.",
    )
    return parser.parse_args()


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
    args = _parse_args()
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

    eligible = [
        p for p in procs
        if p.get("presentation_type") == "image_only" and p.get("related_image_ids")
        and not any(t in (p.get("fru_name") or "").lower() for t in _DIAGNOSTIC)
        and _baseline_image_count(p, figs) <= 4
    ]
    if args.target == "previous-failures":
        targets = _previous_failures(Path(args.previous_report))
        sample = [p for p in eligible if (p.get("manual_id"), p.get("fru_id")) in targets]
    elif args.target == "m8-9-failures":
        targets = _previous_failures(Path("data/eval/m8_9_vision_live_full_final.jsonl"))
        sample = [p for p in eligible if (p.get("manual_id"), p.get("fru_id")) in targets]
    elif args.target == "recovered-regions":
        sample = [p for p in eligible if any("_region_" in str(image_id) for image_id in p.get("related_image_ids", []))]
    else:
        sample = eligible
    limit = args.limit or args.legacy_limit or 0
    if limit:
        sample = sample[:limit]

    name_prompt = (
        "This is a service diagram from a laptop hardware manual. In 6 words or fewer, "
        "name the single component this exploded-view illustrates being removed. "
        "Answer with the component name only."
    )

    previous_failure_targets = _previous_failures(Path("data/eval/m8_9_vision_live_full_final.jsonl"))
    recon_lat, name_lat = [], []
    empty = leaks = fig_correct = fig_total = 0
    scorer_false_negative = 0
    rows = []
    for i, p in enumerate(sample, 1):
        pdf = manuals.get(p["manual_id"])
        primary = vs.primary_figure_metadata(p, figs)
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
                if ok is False and _possible_scorer_false_negative(p["fru_name"], seen):
                    scorer_false_negative += 1
                if ok:
                    fig_correct += 1
            except Exception as exc:  # noqa: BLE001
                seen = f"ERROR {exc}"
            name_lat.append(time.time() - t1)
        rows.append(
            {
                "manual": p["manual_id"],
                "fru_id": p["fru_id"],
                "fru_name": p["fru_name"],
                "related_image_ids": p.get("related_image_ids") or [],
                "previous_m8_9_failure": (p.get("manual_id"), p.get("fru_id")) in previous_failure_targets,
                **primary,
                "steps": len(steps),
                "leaks": leaked,
                "fig_seen": seen,
                "fig_ok": ok,
                "possible_scorer_false_negative": ok is False
                and _possible_scorer_false_negative(p["fru_name"], seen),
            }
        )
        if i % 20 == 0:
            print(f"  ...{i}/{len(sample)} done")

    def p95(xs):
        xs = sorted(xs)
        return xs[int(len(xs) * 0.95) - 1] if len(xs) > 1 else (xs[0] if xs else 0)

    print(f"\n=== ThinkPad vision live eval: target={args.target} n={len(sample)} image_only FRUs ===")
    print(f"reconstruction: non-empty={len(sample)-empty}/{len(sample)} ({100*(len(sample)-empty)//max(len(sample),1)}%)  spec_leaks={leaks}")
    print(f"figure correctness (qwen-vl names returned image == queried FRU): {fig_correct}/{fig_total} ({100*fig_correct//max(fig_total,1)}%)")
    print(f"latency reconstruct: mean={sum(recon_lat)/max(len(recon_lat),1):.1f}s p95={p95(recon_lat):.1f}s")
    print(f"latency name-check: mean={sum(name_lat)/max(len(name_lat),1):.1f}s p95={p95(name_lat):.1f}s")
    print(f"possible scorer false-negatives: {scorer_false_negative}")
    print("\n--- figure MISMATCHES (returned image may not match FRU) ---")
    for r in rows:
        if r["fig_ok"] is False:
            print(f"  {r['manual'][:22]} {r['fru_id']} expected='{r['fru_name'][:26]}' seen='{r['fig_seen']}'")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"\nper-FRU report (gitignored): {out}")
    return 0


def _possible_scorer_false_negative(expected: str, seen: str) -> bool:
    exp, got = _tokens(expected), _tokens(seen)
    for left in exp:
        for right in got:
            if _edit_distance(left, right) <= 2 and min(len(left), len(right)) >= 4:
                return True
    return False


def _baseline_image_count(procedure: dict, figures: dict[str, dict]) -> int:
    """Count evidence images using the M8.9 population rule.

    M8.10 appends `region_crop_precise` diagnostics to the same procedure
    payload. Those should not make an otherwise M8.9-eligible case disappear
    from the live evaluator population.
    """

    count = 0
    for image_id in procedure.get("related_image_ids") or []:
        figure = figures.get(str(image_id)) or {}
        if figure.get("figure_kind") == "region_crop_precise":
            continue
        count += 1
    return count


def _edit_distance(left: str, right: str) -> int:
    prev = list(range(len(right) + 1))
    for i, char_left in enumerate(left, start=1):
        cur = [i]
        for j, char_right in enumerate(right, start=1):
            cur.append(
                min(
                    cur[-1] + 1,
                    prev[j] + 1,
                    prev[j - 1] + (0 if char_left == char_right else 1),
                )
            )
        prev = cur
    return prev[-1]


def _previous_failures(path: Path) -> set[tuple[str, str]]:
    targets: set[tuple[str, str]] = set()
    if not path.exists():
        return targets
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("fig_ok") is False:
            targets.add((row.get("manual"), row.get("fru_id")))
    return targets


if __name__ == "__main__":
    raise SystemExit(main())
