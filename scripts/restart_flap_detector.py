#!/usr/bin/env python3
"""
restart_flap_detector.py — catches SLOW-DRIP service flapping that neither
systemd's own StartLimitBurst nor opscenter_watchdog.py's crash-loop check
can see.

WHY THIS EXISTS (incident 2026-07-09):
  thunderbird-telegram-gw.service restarted 58x in 5 days. Nothing caught it:
    - systemd Restart=always + StartLimitIntervalSec=300/StartLimitBurst=5
      only fires on a TIGHT burst (5 crashes in 5 min). This pattern was one
      restart every ~1-3 hours — never close to that window.
    - opscenter_watchdog.py's CRASH_LOOP_THRESHOLD (3 restarts / 10 min) has
      the same blind spot, AND only records a restart in its own
      `restart_history` when IT is the one that restarts the service. Since
      systemd's Restart=always resurrects the process in ~10s — faster than
      the watchdog's 2-min poll — `_is_service_active()` never observes it
      down, so the watchdog's own history stays empty. It was structurally
      blind to systemd-initiated restarts, full stop.
    - systemd's own NRestarts counter (`systemctl show --property=NRestarts`)
      IS live ground truth, but nothing polls it AND it gets silently zeroed
      by watchdog's own `_reset_failed_service()` (`systemctl reset-failed`)
      every time it runs the down-branch — so even reading NRestarts
      opportunistically loses history between polls.
    - Healthchecks.io (self-hosted, :8123) is dead-man-switch only (alerts on
      a MISSED ping); it has no restart-frequency / flapping concept — verified
      against its own docs. Also: at time of this audit the container itself
      reports `unhealthy` (fetchstatus.py crashes on Python 3.14's stricter
      urllib HTTPError handling) — a second, independent bug found for free.

FIX: journalctl is the one ground truth that survives counter resets and
   short windows — every full start cycle logs exactly one
   "Started <description>" line, whether triggered by systemd, a human, or
   this watchdog. Count those lines over a WIDE window (24h + 7d) per unit.
   Zero new infra. Zero new memory footprint. No root required (--user units).

USAGE:
  python3 scripts/restart_flap_detector.py                 # scan + report
  python3 scripts/restart_flap_detector.py --unit thunderbird-telegram-gw.service
  python3 scripts/restart_flap_detector.py --window-days 5 --json
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
STATE_FILE = ROOT / "logs" / "restart_flap_state.json"

# Thresholds — tunable per unit; DEFAULT applies to anything not listed.
# These are deliberately generous (an operator's judgment call, not a hard
# science): the point is to catch "58 in 5 days", not to page on 2 restarts.
DEFAULT_THRESHOLDS = {"per_24h": 6, "per_7d": 15}
UNIT_THRESHOLDS: dict[str, dict] = {
    # long-poll network services legitimately reconnect more than a batch job
    "thunderbird-telegram-gw.service": {"per_24h": 8, "per_7d": 20},
}

START_RE = re.compile(r": Started ")


def _log_flap_plan(flagged: dict, state_file: Path) -> None:
    """Open+close a trivial Hale Orchestrator Plan for this scan, per
    docs/superpowers/specs/2026-07-09-self-healing-architecture-reverse-engineered.md.
    Called AFTER the scan already wrote its state file — a ledger entry,
    never a gate on the detector's own exit-code signal. Lazy import +
    broad except: this script runs unattended via systemd timer and must
    never fail its actual detection job over a ledger-write problem."""
    if not flagged:
        return
    try:
        from core.ops.hale_orchestrator import open_plan, assess_plan, close_plan
        units = ", ".join(sorted(flagged))
        plan = open_plan(
            task_summary=f"restart-flap flagged: {units}",
            tier="trivial",
            criteria=[f"flagged units recorded to {state_file}"],
        )
        status = "met" if state_file.exists() else "unverified"
        result = assess_plan(plan, {plan.criteria[0]: status})
        close_plan(result)
    except Exception:
        pass


def _discover_units() -> list[str]:
    """All --user units whose name suggests they're Wing-owned long-running
    daemons (not oneshot timers — those are expected to start/stop by design)."""
    out = subprocess.run(
        ["systemctl", "--user", "list-units", "--type=service", "--all",
         "--no-legend", "--no-pager", "--plain"],
        capture_output=True, text=True, timeout=15,
    ).stdout
    units = []
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        if name.startswith(("thunderbird-", "d2m-", "ai-auth-probe", "hale-",
                             "elon-", "claude-", "tess-", "portal-", "opencode-")):
            units.append(name)
    return sorted(set(units))


def _count_starts(unit: str, since: str) -> int:
    try:
        out = subprocess.run(
            ["journalctl", "--user", "-u", unit, "--since", since,
             "--no-pager", "-o", "short-iso"],
            capture_output=True, text=True, timeout=20,
        ).stdout
    except Exception:
        return -1
    return sum(1 for line in out.splitlines() if START_RE.search(line))


def scan(units: list[str], window_days: int) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    results = {}
    for unit in units:
        c24 = _count_starts(unit, "24 hours ago")
        c7d = _count_starts(unit, f"{window_days} days ago")
        th = UNIT_THRESHOLDS.get(unit, DEFAULT_THRESHOLDS)
        flag_24h = c24 >= th["per_24h"]
        flag_7d = c7d >= th["per_7d"]
        results[unit] = {
            "starts_24h": c24,
            "starts_7d": c7d,
            "threshold_24h": th["per_24h"],
            "threshold_7d": th["per_7d"],
            "FLAGGED": flag_24h or flag_7d,
        }
    return {"scanned_at": now, "window_days": window_days, "units": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", help="scan a single unit instead of auto-discovering")
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    units = [args.unit] if args.unit else _discover_units()
    report = scan(units, args.window_days)

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(report, indent=2))

    flagged = {u: r for u, r in report["units"].items() if r["FLAGGED"]}
    _log_flap_plan(flagged, STATE_FILE)

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"restart_flap_detector — {len(report['units'])} units scanned, "
          f"window={args.window_days}d")
    for unit, r in sorted(report["units"].items(), key=lambda kv: -kv[1]["starts_7d"]):
        marker = "🔴 FLAGGED" if r["FLAGGED"] else "  ok"
        print(f"  {marker}  {unit:45s} 24h={r['starts_24h']:>3}  "
              f"7d={r['starts_7d']:>3}  (thresh 24h={r['threshold_24h']} 7d={r['threshold_7d']})")

    if flagged:
        print(f"\n{len(flagged)} unit(s) flapping beyond threshold — "
              f"none of systemd's StartLimitBurst, opscenter_watchdog's "
              f"crash-loop window, or Healthchecks dead-man-switch would "
              f"have caught this pattern.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
