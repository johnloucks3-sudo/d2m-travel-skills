#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Nightly Tech Harvest
========================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Replaces the old tech-adoption health_probe (`test -f ...`), which only checked
that a file EXISTED. A file can exist and emit "0 tools" for 8 days straight —
exactly what happened Jun 13–21, 2026, undetected until the Commander asked.

This probe checks EFFICACY, not presence:
  RED (exit 1) if the harvest did not run recently (stale output), or if its
  fetchers are degraded (almost no source returned content). A genuinely quiet
  day (sources fetched fine, just nothing HIGH) is HEALTHY and exits 0 — we
  distinguish a *silent sensor* (broken) from a *quiet sensor* (working).

Exit 0 = RAZOR_SHARP. Exit 1 = degraded (CI sweep escalates DULL→RED→REPLACE
on consecutive failures per the registry replacement engine).
"""
import json
import sys
import time
from pathlib import Path

LATEST = Path.home() / "Thunderbird" / "logs" / "tech_harvest_latest.json"

STALE_HOURS      = 30   # daily cadence — >30h means a run was missed
MIN_NONEMPTY_SRC = 2    # fewer sources returning content => fetchers broken


def fail(msg: str) -> "NoReturn":
    print(f"RED tech-harvest: {msg}")
    sys.exit(1)


def main() -> None:
    if not LATEST.exists():
        fail("no tech_harvest_latest.json — harvester has never produced output")

    age_h = (time.time() - LATEST.stat().st_mtime) / 3600.0
    if age_h > STALE_HOURS:
        fail(f"stale: last harvest {age_h:.1f}h ago (cadence is daily) — the job stopped running")

    try:
        d = json.loads(LATEST.read_text())
    except Exception as e:
        fail(f"latest harvest file unreadable: {e}")

    findings = d.get("findings", [])
    non_empty = sum(1 for f in findings if f.get("content"))
    total     = d.get("sources_count", len(findings))

    if non_empty < MIN_NONEMPTY_SRC:
        fail(f"fetchers degraded: only {non_empty}/{total} sources returned content "
             f"(silent-sensor failure mode)")

    # Healthy — note whether it was a quiet day vs an active one.
    hi = d.get("high_count", 0)
    print(f"RAZOR_SHARP tech-harvest: {age_h:.1f}h old, {non_empty}/{total} sources live, "
          f"{hi} HIGH signal(s)")
    sys.exit(0)


if __name__ == "__main__":
    main()
