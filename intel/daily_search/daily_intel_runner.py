#!/usr/bin/env python3
"""
Thunderbird Daily Intelligence Runner
Fires every morning at 0900 MT via systemd timer.
Runs 4 waves (configurable). ELON + Whetstone own inter-wave prompt evolution.
Hale decides implementation. EOD summary to Commander.
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
WAVES_PER_DAY = int(os.getenv("INTEL_WAVES", "4"))
PPLX_KEY      = os.getenv("PERPLEXITY_API_KEY", "")

# ── Helpers ───────────────────────────────────────────────────────────────────

def next_wave_number() -> int:
    """Read existing wave files to find the highest wave number, return +1."""
    files = sorted(SEARCH_DIR.glob("wave*.json"))
    if not files:
        return 1
    nums = []
    for f in files:
        try:
            nums.append(int(f.name.split("_")[0].replace("wave", "")))
        except ValueError:
            pass
    return max(nums) + 1 if nums else 1


def run_wave(wave_num: int, category_ids: list = None) -> dict:
    """Run a single wave. Returns parsed JSON results dict."""
    env = dict(os.environ)
    env["SEARCH_WAVE"]       = str(wave_num)
    env["PERPLEXITY_API_KEY"] = PPLX_KEY

    args = [sys.executable, str(SEARCH_SCRIPT)]
    if category_ids:
        args += [str(i) for i in category_ids]

    log_path = LOG_DIR / f"daily_intel_wave{wave_num}.log"
    print(f"\n{'='*60}")
    print(f"  LAUNCHING WAVE {wave_num}  |  {datetime.now(MT).strftime('%H:%M MT')}")
    if category_ids:
        print(f"  Categories: {category_ids}")
    print(f"  Log: {log_path}")
    print(f"{'='*60}")

    t0 = time.time()
    with open(log_path, "w") as log_f:
        proc = subprocess.run(
            args, env=env, cwd=str(REPO_ROOT),
            stdout=log_f, stderr=subprocess.STDOUT,
            timeout=300,
        )

    elapsed = round(time.time() - t0, 1)
    print(f"  Wave {wave_num} done in {elapsed}s. Exit: {proc.returncode}")

    # Find the output file
    output_files = sorted(SEARCH_DIR.glob(f"wave{wave_num}_*.json"), reverse=True)
    if not output_files:
        print(f"  WARNING: No output file found for wave {wave_num}")
        return {}

    output_path = output_files[0]
    print(f"  Output: {output_path.name}")
    return json.loads(output_path.read_text())


def summarize_wave(wave_data: dict) -> str:
    """One-paragraph summary of a wave's results for EOD brief."""
    results = wave_data.get("results", [])
    hits    = [r for r in results if r.get("result")]
    errors  = [r for r in results if r.get("error")]
    dead    = [r for r in hits if ("can't" in (r.get("result") or "")[:300].lower()
                                   or "cannot" in (r.get("result") or "")[:300].lower()
                                   or "not contain" in (r.get("result") or "")[:300].lower())]
    signal  = [r for r in hits if r not in dead]

    lines = [
        f"Wave {wave_data.get('wave','?')}: {len(results)} categories · "
        f"{len(signal)} signal · {len(dead)} weak · {len(errors)} errors",
    ]
    for r in signal:
        preview = (r.get("result") or "")[:200].replace("\n", " ")
        lines.append(f"  [{r['id']:02d}] {r['name']}: {preview}")
    return "\n".join(lines)


def send_eod_summary(day_results: list[dict]) -> None:
    """Send EOD summary to Commander via Telegram."""
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from core.comms.wing_page import send_page

        ts   = datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")
        date = datetime.now(MT).strftime("%Y-%m-%d")

        total_cats = sum(len(d.get("results", [])) for d in day_results)
        total_hits = sum(
            sum(1 for r in d.get("results", []) if r.get("result"))
            for d in day_results
        )
        cost_est = round(total_cats * 0.005, 2)

        body = [
            f"⚡ DAILY INTEL EOD — {date}",
            f"{len(day_results)} waves · {total_cats} searches · {total_hits} hits · ~${cost_est}",
            "",
        ]
        for wd in day_results:
            body.append(summarize_wave(wd))
            body.append("")

        body += [
            "Full results in intel/daily_search/",
            f"— V. Hale, VCS · {ts}",
        ]

        send_page("\n".join(body))
        print("\n  EOD summary sent to Telegram.")
    except Exception as exc:
        print(f"\n  EOD summary failed: {exc}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not PPLX_KEY:
        print("ERROR: PERPLEXITY_API_KEY not set. Aborting.")
        sys.exit(1)

    start_wave = next_wave_number()
    day_results = []

    print(f"\n{'='*60}")
    print(f"  THUNDERBIRD DAILY INTELLIGENCE — {datetime.now(MT).strftime('%Y-%m-%d %H:%M MT')}")
    print(f"  Starting at wave {start_wave}. Running {WAVES_PER_DAY} waves.")
    print(f"{'='*60}")

    for i in range(WAVES_PER_DAY):
        wave_num  = start_wave + i
        wave_data = run_wave(wave_num)
        day_results.append(wave_data)

        if i < WAVES_PER_DAY - 1:
            print(f"\n  [pause 10s before wave {wave_num + 1} — ELON/Whetstone analyze async]")
            time.sleep(10)

    send_eod_summary(day_results)

    print(f"\n  Daily run complete. {WAVES_PER_DAY} waves fired.")
    print(f"  Output: {SEARCH_DIR}/wave*.json")


if __name__ == "__main__":
    main()
