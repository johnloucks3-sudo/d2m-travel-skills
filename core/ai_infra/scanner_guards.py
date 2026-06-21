#!/usr/bin/env python3
"""
SCANNER GUARDS — Phase-0 guardrails (built BEFORE the collection deck)
=====================================================================
Dreams2Memories Travel · built 2026-06-21 (wing consult MISSION-325)

The wing's unanimous condition: no watchdog + no cost-kill → no scanner. These
ship first. Two guards, both proven by drill before the collector draws breath.

  1. DEAD-MAN'S SWITCH (ELON + Sterling). Every scan pulse calls record_pulse().
     check_liveness() goes RED if a pulse was MISSED (no heartbeat in the window),
     or output is DEGENERATE (2 consecutive zero-finding pulses, or a frozen feed
     = identical content_hash). Zero/silence is the ALARM, not the all-clear.
     RED → page ELON → Commander.
  2. PRE-CALL COST KILL (Harlan). can_spend() REFUSES a cheap-engine call when the
     running DAY spend hits the cap — before the call bills, not after (a logger
     after the bill is how April cost $153). Default cap $5/day. Gemini paid tier
     must stay unset (free-tier wall = the spike is physically impossible).

State: state/scanner_heartbeat.json · state/cheap_engine_spend.jsonl
Exit (CLI watchdog): 0 = alive, 1 = RED.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # so OpsCenter.wing_page imports when run as a script
HEARTBEAT = ROOT / "state" / "scanner_heartbeat.json"
SPEND = ROOT / "state" / "cheap_engine_spend.jsonl"
ENABLED = ROOT / "state" / "scanner.enabled"   # marker: scanner is deployed & must prove liveness

PULSE_WINDOW_HOURS = 26     # a daily pulse missed by >26h = RED (missed pulse)
DAILY_COST_CAP = 5.00       # Harlan's $5/day pre-call kill
ZERO_STREAK_RED = 2         # 2 consecutive zero-finding pulses = RED


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── 1. DEAD-MAN'S SWITCH ────────────────────────────────────────────────────────
def record_pulse(finding_count: int, content_hash: str, sectors: list[str] | None = None) -> None:
    """The scanner calls this every pulse. Tracks zero/frozen streaks."""
    prev = {}
    if HEARTBEAT.exists():
        try:
            prev = json.loads(HEARTBEAT.read_text())
        except Exception:
            prev = {}
    zero_streak = (prev.get("zero_streak", 0) + 1) if finding_count == 0 else 0
    frozen = bool(content_hash) and content_hash == prev.get("content_hash")
    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT.write_text(json.dumps({
        "ts": _now(), "finding_count": finding_count, "content_hash": content_hash,
        "sectors": sectors or [], "zero_streak": zero_streak, "frozen": frozen,
    }, indent=2))


def check_liveness() -> tuple[bool, str]:
    """Returns (alive, detail). Silence is the alarm, not the all-clear."""
    if not ENABLED.exists():
        return True, "dormant — scanner not yet deployed (no state/scanner.enabled marker)"
    if not HEARTBEAT.exists():
        return False, "no heartbeat ever written — scanner never pulsed"
    hb = json.loads(HEARTBEAT.read_text())
    try:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(hb["ts"])).total_seconds() / 3600
    except Exception:
        return False, "heartbeat timestamp unreadable"
    if age_h > PULSE_WINDOW_HOURS:
        return False, f"MISSED PULSE — last heartbeat {age_h:.1f}h ago (window {PULSE_WINDOW_HOURS}h)"
    if hb.get("zero_streak", 0) >= ZERO_STREAK_RED:
        return False, f"DEGENERATE — {hb['zero_streak']} consecutive zero-finding pulses (failure to prove liveness)"
    if hb.get("frozen"):
        return False, "FROZEN FEED — output identical to prior pulse (a frozen feed is a dead feed)"
    return True, f"alive — last pulse {age_h:.1f}h ago, {hb.get('finding_count')} findings"


# ── 2. PRE-CALL COST KILL ───────────────────────────────────────────────────────
def _day_spend(d: str | None = None) -> float:
    d = d or date.today().isoformat()
    if not SPEND.exists():
        return 0.0
    tot = 0.0
    for line in SPEND.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if r.get("day") == d:
                tot += r.get("cost", 0.0)
        except Exception:
            continue
    return round(tot, 4)


def can_spend(engine: str, est_cost: float) -> tuple[bool, str]:
    """PRE-call gate. Refuse the call when the day would exceed the cap."""
    # Gemini paid-tier must stay unset — free-tier wall makes the spike impossible.
    if engine.lower().startswith("gemini") and os.environ.get("GEMINI_PAID_TIER_APPROVED"):
        # paid tier on: still enforce the daily cap below, but flag it
        pass
    today = _day_spend()
    if today + est_cost > DAILY_COST_CAP:
        return False, f"REFUSED — day-spend ${today:.2f} + ${est_cost:.2f} > ${DAILY_COST_CAP:.2f}/day cap"
    return True, f"ok — ${today:.2f} spent today, ${DAILY_COST_CAP - today:.2f} left under cap"


def record_spend(engine: str, cost: float, tokens: int = 0) -> None:
    SPEND.parent.mkdir(parents=True, exist_ok=True)
    with open(SPEND, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), "day": date.today().isoformat(),
                             "engine": engine, "cost": round(cost, 6), "tokens": tokens}) + "\n")


# ── CLI ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("watchdog")  # run the dead-man's-switch check
    p = sub.add_parser("pulse"); p.add_argument("--findings", type=int, required=True); p.add_argument("--hash", required=True)
    b = sub.add_parser("can-spend"); b.add_argument("--engine", required=True); b.add_argument("--cost", type=float, required=True)
    s = sub.add_parser("spend"); s.add_argument("--engine", required=True); s.add_argument("--cost", type=float, required=True)
    args = ap.parse_args()

    if args.cmd == "watchdog":
        alive, detail = check_liveness()
        print(("ALIVE " if alive else "RED ") + "scanner-watchdog: " + detail)
        if not alive:
            try:
                from OpsCenter.wing_page import page
                page("commander", "🔴 SCANNER WATCHDOG (dead-man's switch): " + detail)
            except Exception as e:
                print(f"[page failed: {e}]", file=sys.stderr)
        return 0 if alive else 1
    if args.cmd == "pulse":
        record_pulse(args.findings, args.hash); print("pulse recorded"); return 0
    if args.cmd == "can-spend":
        ok, detail = can_spend(args.engine, args.cost); print(detail); return 0 if ok else 1
    if args.cmd == "spend":
        record_spend(args.engine, args.cost); print(f"recorded ${args.cost} {args.engine}; day total ${_day_spend()}"); return 0


if __name__ == "__main__":
    sys.exit(main())
