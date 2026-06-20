#!/usr/bin/env python3
"""ci_sentinel.py — Armed Overwatch (Self-Observability), run as the F2T2EA kill chain.

Born from the 10-hour blind spot (2026-06-20): 136 timers + health-checks watched
LIVENESS only; 3 services crash-looped ~78,000 errors with zero indicator. This is
multispectral ISR + organic strike that closes the loop WITHOUT paging the Commander
unless the fix genuinely needs him (sudo / spend / client-send).

F2T2EA:
  FIND    — overwatch: multispectral scan of every user service (restarts, error-rate,
            failed-state, port-conflict bands fused).
  FIX     — pinpoint: which unit + which bands tripped.
  TRACK   — custody: cooldown state so we don't re-engage the same target repeatedly.
  TARGET  — assign weapon: ensure the alert bird (managed agent) is armed.
  ENGAGE  — scramble: managed-agent fixer diagnoses + repairs root cause (CI authority).
  ASSESS  — BDA: re-scan the unit; resolved only if every band is clean. If not resolved
            OR the agent escalated → page the Commander (the only time he's paged).

Usage:
  python3 scripts/ci_sentinel.py            # full F2T2EA loop
  python3 scripts/ci_sentinel.py --dry-run  # FIND+FIX only (report, no engage)
  python3 scripts/ci_sentinel.py --json
"""
import argparse
import json
import sys
from datetime import datetime, timezone
sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.self_observability import (
    scan, assess, arm_alert, dispatch_remediation, escalate_to_commander,
    should_dispatch, is_escalation, notify_hale, OverwatchBlind,
    _load_state, _save_state, QRA_FLIGHT_SIZE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="FIND+FIX only; no engage")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    log = []

    # FIND (overwatch) + FIX (pinpoint)
    try:
        breaches = scan()
    except OverwatchBlind as e:
        # The sensor failed — NEVER report 'clean'. Make Hale aware + escalate.
        notify_hale("OVERWATCH_BLIND", "sentinel", str(e))
        escalate_to_commander("ci-sentinel", f"Overwatch blind: {e}")
        print(f"🔴 OVERWATCH BLIND: {e}", file=sys.stderr)
        return 3
    if not breaches:
        if args.json:
            print(json.dumps({"status": "clean", "breaches": []}))
        else:
            print("✅ Armed overwatch: all services clean across all bands.")
        return 0

    state = _load_state()
    # Weapons generation — arm the alert bird once (QRA on the pad), then run the cycle per target.
    armed = arm_alert() if not args.dry_run else {"armed": "dry-run"}

    engaged = 0
    for b in breaches:
        unit = b["unit"]
        entry = {"unit": unit, "bands": b["reasons"]}

        if args.dry_run:
            entry["phase"] = "FIND+FIX (dry-run, no engage)"
            log.append(entry)
            continue

        # TRACK — maintain custody; cooldown so we don't re-engage a held target
        if not should_dispatch(unit, state, now):
            entry["phase"] = "TRACK (cooldown — holding custody, recently engaged)"
            log.append(entry)
            continue
        # TARGET — clear to engage; QRA flight size caps simultaneous weapon assignment
        if engaged >= QRA_FLIGHT_SIZE:
            entry["phase"] = f"TARGET held (QRA flight full @ {QRA_FLIGHT_SIZE}; next cycle)"
            log.append(entry)
            continue

        # ENGAGE — scramble the alert bird under a PRIORITY WINDOW so the fixer
        # preempts routine timer traffic (the starvation that timed out Commander comms).
        from core.ci.model_priority import priority_window
        with priority_window("hale-ci", f"CI remediation: {unit}", owner_class="ci", ttl_seconds=240):
            strike = dispatch_remediation(b)
        # Persist cooldown IMMEDIATELY — a crash after dispatch must not lose custody (IMPORT-3)
        state.setdefault(unit, {})["last_dispatch"] = now.isoformat()
        _save_state(state)
        engaged += 1
        entry["engage"] = {"via": strike.get("via"), "dispatched": strike.get("dispatched")}
        # AWARENESS — the accountable owner (Hale) is told of every engagement
        notify_hale("ENGAGE", unit, f"bands: {'; '.join(b['reasons'])}; via {strike.get('via')}")

        if not strike.get("dispatched"):
            escalate_to_commander(unit, f"fixer could not launch: {strike.get('error')}")
            notify_hale("ESCALATE", unit, f"fixer could not launch: {strike.get('error')}")
            entry["phase"] = "ENGAGE FAILED → escalated to Commander"
            log.append(entry)
            continue

        # ASSESS (BDA) — only meaningful for synchronous managed strikes
        if strike.get("via") == "managed_alert":
            agent_said_escalate = strike.get("escalate") or is_escalation(strike.get("output", ""))
            bda = assess(unit)
            entry["assess"] = {"resolved": bda["resolved"], "residual": bda["residual"]}
            if bda["resolved"] and not agent_said_escalate:
                notify_hale("RESOLVED", unit, "target neutralized (all bands clean)")
                entry["phase"] = "ASSESS: ✅ target neutralized (all bands clean)"
            else:
                detail = ("agent requested escalation; " if agent_said_escalate else "") + \
                         (f"residual: {bda['residual']}" if bda["residual"] else "")
                escalate_to_commander(unit, detail)
                notify_hale("ESCALATE", unit, detail)
                entry["phase"] = "ASSESS: ✗ not neutralized → escalated to Commander"
        else:
            # headless fallback is async/detached — BDA happens next cycle's FIND
            entry["phase"] = "ENGAGE (headless fallback, detached); ASSESS next cycle"
        log.append(entry)

    if not args.dry_run:
        _save_state(state)

    if args.json:
        print(json.dumps({"status": "breaches", "armed": armed, "log": log}, indent=2))
    else:
        for e in log:
            print(f"🎯 {e['unit']}: {'; '.join(e['bands'])}")
            print(f"    → {e.get('phase')}")

    return 2  # breaches handled (distinct from 1=crash, 3=overwatch-blind)


if __name__ == "__main__":
    sys.exit(main())
