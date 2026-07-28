#!/usr/bin/env python3
"""
Thunderbird Daily Intelligence Runner
Fires every morning at 0900 MT via systemd timer.

6 waves (configurable). After each wave, the inter-wave analyst scores every
category, sharpens queries toward implementable tools, and writes
categories_live.json for the next wave to pick up automatically.

ELON + Whetstone doctrine encoded in inter_wave_analyst.py.
Hale decides implementation; Commander reads the EOD synthesis.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT     = Path(__file__).resolve().parents[2]
SEARCH_DIR    = REPO_ROOT / "intel" / "daily_search"
SEARCH_SCRIPT = SEARCH_DIR / "thunderbird_daily_search.py"
LOG_DIR       = REPO_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

MT            = ZoneInfo("America/Denver")
WAVES_PER_DAY = int(os.getenv("INTEL_WAVES", "6"))
PPLX_KEY      = os.getenv("PERPLEXITY_API_KEY", "")

# Cost kill switch: abort if estimated daily spend exceeds this (USD)
DAILY_COST_CAP = float(os.getenv("INTEL_COST_CAP", "2.00"))
COST_PER_CAT   = 0.005   # ~$0.005/Perplexity sonar call

# ── Helpers ───────────────────────────────────────────────────────────────────

def next_wave_number() -> int:
    """Read existing wave files to find the highest wave number, return +1."""
    files = sorted(SEARCH_DIR.glob("wave*.json"))
    nums  = []
    for f in files:
        try:
            nums.append(int(f.name.split("_")[0].replace("wave", "")))
        except ValueError:
            pass
    return max(nums) + 1 if nums else 1


def run_wave(wave_num: int, category_ids: list = None) -> dict:
    """Run one wave. Returns parsed JSON results dict."""
    env = dict(os.environ)
    env["SEARCH_WAVE"]        = str(wave_num)
    env["PERPLEXITY_API_KEY"] = PPLX_KEY
    env["SERPER_API_KEY"]     = os.getenv("SERPER_API_KEY", "")

    args = [sys.executable, str(SEARCH_SCRIPT)]
    if category_ids:
        args += [str(i) for i in category_ids]

    log_path = LOG_DIR / f"daily_intel_wave{wave_num}.log"
    print(f"\n{'='*62}")
    print(f"  LAUNCHING WAVE {wave_num}  |  {datetime.now(MT).strftime('%H:%M MT')}")
    if category_ids:
        print(f"  Categories subset: {category_ids}")
    print(f"  Log: {log_path.name}")
    print(f"{'='*62}")

    t0 = time.time()
    with open(log_path, "w") as lf:
        proc = subprocess.run(
            args, env=env, cwd=str(REPO_ROOT),
            stdout=lf, stderr=subprocess.STDOUT,
            timeout=360,
        )

    elapsed = round(time.time() - t0, 1)
    print(f"  Wave {wave_num} done in {elapsed}s  |  exit={proc.returncode}")

    output_files = sorted(SEARCH_DIR.glob(f"wave{wave_num}_*.json"), reverse=True)
    if not output_files:
        print(f"  WARNING: No output file for wave {wave_num}")
        return {}

    out = output_files[0]
    print(f"  Output: {out.name}")
    return json.loads(out.read_text())


def inter_wave_analysis(wave_data: dict, wave_num: int) -> int:
    """
    Run inter-wave analyst: score wave, evolve categories, write categories_live.json.
    Returns number of evolved categories written.
    """
    sys.path.insert(0, str(SEARCH_DIR))
    try:
        import inter_wave_analyst as analyst
    except ImportError as e:
        print(f"  [analyst] Import failed: {e} — skipping evolution")
        return 0

    # Find the wave output file
    wave_files = sorted(SEARCH_DIR.glob(f"wave{wave_num}_*.json"), reverse=True)
    if not wave_files:
        print(f"  [analyst] No wave file found for wave {wave_num} — skipping")
        return 0

    wave_path = wave_files[0]

    # Load base categories from the search script
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("search", str(SEARCH_SCRIPT))
        mod  = importlib.util.module_from_spec(spec)
        # Temporarily hide the override so we get the base categories
        live_file = SEARCH_DIR / "categories_live.json"
        hidden    = None
        if live_file.exists():
            hidden = live_file.read_bytes()
            live_file.unlink()
        spec.loader.exec_module(mod)
        base_cats = mod.CATEGORIES
        if hidden is not None:
            live_file.write_bytes(hidden)
    except Exception as e:
        print(f"  [analyst] Could not load base categories: {e} — skipping")
        return 0

    # Score and print report
    scored = analyst.analyze_wave(wave_path)
    analyst.print_wave_report(scored, wave_num)

    # Evolve categories
    evolved = analyst.evolve_categories(base_cats, wave_path, wave_num)

    # Write for next wave
    out_path = analyst.write_categories_live(evolved)
    print(f"  [analyst] {len(evolved)} evolved categories → {out_path.name}")
    return len(evolved)


def summarize_wave(wave_data: dict) -> str:
    """One-paragraph wave summary for EOD brief."""
    results = wave_data.get("results", [])
    hits    = [r for r in results if r.get("result")]
    errors  = [r for r in results if r.get("error")]
    dead    = [r for r in hits if any(
        kw in (r.get("result") or "")[:300].lower()
        for kw in ("can't", "cannot", "not contain", "unrelated")
    )]
    signal  = [r for r in hits if r not in dead]

    lines = [
        f"Wave {wave_data.get('wave','?')}: {len(results)} cats · "
        f"{len(signal)} signal · {len(dead)} weak · {len(errors)} errors",
    ]
    for r in signal[:8]:
        preview = (r.get("result") or "")[:180].replace("\n", " ")
        lines.append(f"  [{r['id']:02d}] {r['name']}: {preview}")
    return "\n".join(lines)


def build_eod_synthesis(day_results: list, all_wave_paths: list) -> str:
    """Build EOD synthesis: top signals + implementation candidates."""
    sys.path.insert(0, str(SEARCH_DIR))
    try:
        import inter_wave_analyst as analyst
        top5 = analyst.top_signals_eod(all_wave_paths, n=5)
    except Exception:
        top5 = []

    ts   = datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")
    date = datetime.now(MT).strftime("%Y-%m-%d")

    total_cats = sum(len(d.get("results", [])) for d in day_results)
    total_hits = sum(
        sum(1 for r in d.get("results", []) if r.get("result") and not any(
            kw in (r.get("result") or "")[:200].lower()
            for kw in ("can't", "cannot", "unrelated")
        ))
        for d in day_results
    )
    cost_est = round(total_cats * COST_PER_CAT, 2)

    lines = [
        f"⚡ DAILY INTEL EOD — {date}",
        f"{len(day_results)} waves · {total_cats} searches · {total_hits} clean hits · ~${cost_est}",
        "",
        "━━ TOP 5 SIGNALS (cross-wave) ━━",
    ]
    if top5:
        for i, s in enumerate(top5, 1):
            lines.append(f"  {i}. [{s['id']:02d}] {s['name']} (score={s['score']})")
            lines.append(f"     {s['result_preview'][:200]}")
            lines.append("")
    else:
        lines.append("  (analyst not available — see wave logs)")
        lines.append("")

    lines += [
        "━━ IMPLEMENTATION CANDIDATES ━━",
    ]
    impl = [s for s in top5 if s.get("score", 0) >= 40][:3]
    if impl:
        for s in impl:
            lines.append(f"  → {s['name']}: see wave logs for exact install steps")
    else:
        lines.append("  → Review top-5 above; highest scorers are implementation-ready")

    lines += [
        "",
        "Full results: intel/daily_search/wave*.json",
        f"— V. Hale, VCS · {ts}",
    ]
    return "\n".join(lines)


def send_eod_summary(day_results: list, all_wave_paths: list) -> None:
    """Send EOD synthesis to Commander via Telegram."""
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from core.comms.wing_page import send_page
        body = build_eod_synthesis(day_results, all_wave_paths)
        try:
            from core.staffing.sss_render import render_info_text
            body = render_info_text(
                subject="Daily Market/Competitor Intel Synthesis",
                opr="Dembe (A2)", staffed_by=["Dembe (A2)"],
                purpose="Daily market and competitor intelligence synthesis.",
                discussion=body,
                tag="Market Intel",
            )
        except Exception as e:
            print(f"  sss_render wrap failed (non-fatal, sending unwrapped): {e}")
        send_page(body)
        print("\n  EOD synthesis sent to Telegram.")
    except Exception as exc:
        print(f"\n  EOD send failed: {exc}")
        # Write to disk as fallback
        eod_path = SEARCH_DIR / f"eod_{datetime.now(MT).strftime('%Y-%m-%d')}.txt"
        eod_path.write_text(build_eod_synthesis(day_results, all_wave_paths))
        print(f"  EOD written to {eod_path.name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    serper_key = os.getenv("SERPER_API_KEY", "")
    if not PPLX_KEY and not serper_key:
        print("ERROR: Neither PERPLEXITY_API_KEY nor SERPER_API_KEY set. Aborting.")
        sys.exit(1)
    if not PPLX_KEY and serper_key:
        print("WARNING: PERPLEXITY_API_KEY expired/missing — running on Serper fallback only.")

    start_wave  = next_wave_number()
    day_results = []
    wave_paths  = []
    total_cost  = 0.0

    print(f"\n{'='*62}")
    print(f"  THUNDERBIRD DAILY INTELLIGENCE")
    print(f"  {datetime.now(MT).strftime('%Y-%m-%d %H:%M MT')}  |  {WAVES_PER_DAY} waves planned")
    print(f"  Starting at wave {start_wave}. Cost cap: ${DAILY_COST_CAP:.2f}")
    print(f"{'='*62}")

    # Clear any stale override from a prior run
    stale_override = SEARCH_DIR / "categories_live.json"
    if stale_override.exists():
        stale_override.unlink()
        print(f"  Cleared stale categories_live.json from prior run.")

    for i in range(WAVES_PER_DAY):
        wave_num = start_wave + i

        # Cost kill switch
        if total_cost >= DAILY_COST_CAP:
            print(f"\n  COST CAP ${DAILY_COST_CAP:.2f} reached after wave {wave_num - 1}. Stopping.")
            break

        wave_data = run_wave(wave_num)
        day_results.append(wave_data)

        # Track wave output file for EOD synthesis
        wf = sorted(SEARCH_DIR.glob(f"wave{wave_num}_*.json"), reverse=True)
        if wf:
            wave_paths.append(wf[0])

        n_cats = len(wave_data.get("results", []))
        total_cost += n_cats * COST_PER_CAT
        print(f"  Estimated run cost so far: ${total_cost:.3f}")

        # Inter-wave analysis (not after the last wave)
        if i < WAVES_PER_DAY - 1:
            print(f"\n  ── Inter-wave analysis: wave {wave_num} → wave {wave_num + 1} ──")
            inter_wave_analysis(wave_data, wave_num)
            print(f"  Queries sharpened. Launching wave {wave_num + 1} in 5s...")
            time.sleep(5)

    # Clean up override after run
    override = SEARCH_DIR / "categories_live.json"
    if override.exists():
        override.unlink()

    send_eod_summary(day_results, wave_paths)

    # ELON daily synthesis — one session evaluates all finds, no queue
    try:
        from elon_daily_synthesis import run_elon_synthesis
        synthesis_result = run_elon_synthesis(wave_paths)
        if synthesis_result:
            print(f"  ELON synthesis: {synthesis_result.get('implement_now', 0)} implement | "
                  f"{synthesis_result.get('already_covered', 0)} covered | "
                  f"{synthesis_result.get('escalated', 0)} escalated")
    except Exception as e:
        print(f"  ELON synthesis error: {e}")
        # Fallback to mission-creation pipeline
        try:
            from elon_adopt_pipeline import run_adopt_pipeline, send_adopt_page
            adopt_results = run_adopt_pipeline(wave_paths)
            if adopt_results.get("adopted"):
                send_adopt_page(adopt_results)
        except Exception as e2:
            print(f"  ELON fallback error: {e2}")

    print(f"\n  Daily run complete. {len(day_results)}/{WAVES_PER_DAY} waves fired.")
    print(f"  Total estimated cost: ${total_cost:.3f}")
    print(f"  Output: {SEARCH_DIR}/wave*.json")


if __name__ == "__main__":
    main()
