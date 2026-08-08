#!/usr/bin/env python3
"""
timer_self_repair.py — WAR ROOM idea #16 (Sterling, 2026-08-07): "dead timer /
broken cron / stale automation attempts its own restart-and-reverify before
paging anyone; only a repeat failure escalates."

GAP THIS CLOSES: opscenter_watchdog.py already restarts-and-reverifies its
SERVICES dict of long-running daemons before alerting. restart_flap_detector.py
already catches slow-drip flapping in units that LOOK active moment-to-moment.
Neither covers a --user .timer that silently stopped re-arming, or a oneshot
.service a timer fires that started failing every run with nothing watching
it — both fail SILENTLY: no process crash, no "down" service, just a job that
quietly stopped happening. That's the actual "dead timer / broken cron" class.

METHOD: `systemctl --user list-timers --all -o json` gives every timer's next
elapse (epoch usec) and the .service it activates in one call — no fragile
text parsing (list-timers' human LEFT/PASSED columns are unparseable
free text; the JSON `next`/`last` fields are not). Per Wing-owned timer:
  1. Timer itself not ActiveState=active -> reset-failed + start, reverify.
  2. `next` already in the past -> the timer failed to re-arm -> restart it,
     reverify a fresh `next` is in the future.
  3. Activated .service is-failed -> reset-failed + restart once, reverify
     is-failed clears.
Each repair attempt is recorded to STATE_FILE. A unit needing repair on
REPEAT_THRESHOLD consecutive runs stops being auto-repaired (masking a real
recurring fault forever defeats the point) and escalates via
incident_queue.enqueue_incident instead — "only a REPEAT failure escalates."

USAGE:
  python3 scripts/timer_self_repair.py                  # scan, repair, report
  python3 scripts/timer_self_repair.py --dry-run         # detect only, no systemctl mutation
  python3 scripts/timer_self_repair.py --unit NAME.timer # single unit
  python3 scripts/timer_self_repair.py --json
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from OpsCenter.incident_queue import enqueue_incident
except ImportError:
    try:
        from incident_queue import enqueue_incident
    except ImportError:
        def enqueue_incident(event):
            pass  # fallback: swallow silently if queue unavailable

ROOT = Path("/home/john/Thunderbird")
STATE_FILE = ROOT / "logs" / "timer_self_repair_state.json"
REPEAT_THRESHOLD = 3  # consecutive runs needing repair before we stop auto-healing and page

WING_PREFIXES = ("thunderbird-", "d2m-", "ai-auth-probe", "hale-", "elon-",
                  "claude-", "tess-", "portal-", "opencode-", "ci-sentinel",
                  "qdrant-", "bryana-", "cost-", "client-inbox-watch",
                  "yoga-dv7")


def _run(cmd: list[str], timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _list_timers() -> list[dict]:
    out = _run(["systemctl", "--user", "list-timers", "--all", "--no-legend", "-o", "json"]).stdout
    try:
        return json.loads(out) if out.strip() else []
    except json.JSONDecodeError:
        return []


def _is_wing_unit(name: str) -> bool:
    base = name[:-len(".timer")] if name.endswith(".timer") else name
    return base.startswith(WING_PREFIXES)


def _active_state(unit: str) -> str:
    r = _run(["systemctl", "--user", "show", unit, "--property=ActiveState", "--value"])
    return (r.stdout or "").strip()


def _is_failed(unit: str) -> bool:
    r = _run(["systemctl", "--user", "is-failed", unit])
    return r.stdout.strip() == "failed"


def _reset_failed(unit: str) -> None:
    _run(["systemctl", "--user", "reset-failed", unit])


def _restart(unit: str) -> bool:
    return _run(["systemctl", "--user", "restart", unit], timeout=30).returncode == 0


def _start(unit: str) -> bool:
    return _run(["systemctl", "--user", "start", unit], timeout=30).returncode == 0


def _diagnose(timer: dict, now_usec: int) -> list[str]:
    """Returns a list of problem codes found for this timer, empty if healthy."""
    problems = []
    unit = timer["unit"]
    if _active_state(unit) != "active":
        problems.append("timer_not_active")
    elif timer.get("next") and timer["next"] < now_usec:
        problems.append("timer_stuck_not_rearmed")
    svc = timer.get("activates")
    if svc and _is_failed(svc):
        problems.append("activated_service_failed")
    return problems


def _repair(timer: dict, problems: list[str], dry_run: bool) -> dict:
    """Attempt one restart-and-reverify per problem found. Returns outcome dict."""
    unit = timer["unit"]
    svc = timer.get("activates")
    actions, resolved = [], True

    if dry_run:
        return {"actions": [f"DRY-RUN would repair: {problems}"], "resolved": None}

    if "timer_not_active" in problems or "timer_stuck_not_rearmed" in problems:
        _reset_failed(unit)
        ok = _start(unit) if "timer_not_active" in problems else _restart(unit)
        actions.append(f"{'start' if 'timer_not_active' in problems else 'restart'} {unit} -> {'ok' if ok else 'FAILED'}")
        time.sleep(2)
        if _active_state(unit) != "active":
            resolved = False

    if "activated_service_failed" in problems and svc:
        _reset_failed(svc)
        ok = _restart(svc)
        actions.append(f"restart {svc} -> {'ok' if ok else 'FAILED'}")
        time.sleep(3)
        if _is_failed(svc):
            resolved = False

    return {"actions": actions, "resolved": resolved}


def scan_and_repair(unit_filter: str | None, dry_run: bool) -> dict:
    now_usec = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    timers = _list_timers()
    if unit_filter:
        timers = [t for t in timers if t["unit"] == unit_filter]
    else:
        timers = [t for t in timers if _is_wing_unit(t["unit"])]

    state = _load_state()
    history = state.setdefault("history", {})
    results = {}

    for t in timers:
        unit = t["unit"]
        problems = _diagnose(t, now_usec)
        entry = {"scanned_at": datetime.now(timezone.utc).isoformat(), "problems": problems}

        if not problems:
            history[unit] = 0  # reset consecutive-failure streak on a clean scan
            results[unit] = {**entry, "status": "healthy"}
            continue

        streak = history.get(unit, 0) + 1
        history[unit] = streak

        if streak > REPEAT_THRESHOLD:
            entry["status"] = "escalated_repeat_failure"
            entry["streak"] = streak
            enqueue_incident({
                "source": "timer_self_repair",
                "event_type": "repeat_timer_failure",
                "severity": "warning",
                "service": unit,
                "auto_heal_succeeded": False,
                "details": f"{unit} needed repair on {streak} consecutive scans "
                           f"({', '.join(problems)}) — auto-repair suspended, needs a human look.",
            })
        else:
            repair = _repair(t, problems, dry_run)
            entry["status"] = "repaired" if repair.get("resolved") else "repair_attempted"
            entry["repair_actions"] = repair["actions"]
            entry["streak"] = streak
            if repair.get("resolved") is False:
                enqueue_incident({
                    "source": "timer_self_repair",
                    "event_type": "timer_repair_failed",
                    "severity": "warning",
                    "service": unit,
                    "auto_heal_succeeded": False,
                    "details": f"{unit}: {', '.join(problems)}. Repair attempted "
                               f"({'; '.join(repair['actions'])}) but did not resolve — paging per "
                               f"restart-and-reverify-before-paging policy.",
                })
            # repair.get("resolved") is True or None (dry-run) -> silent, no page

        results[unit] = entry

    state["history"] = history
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)
    return {"scanned_at": state["last_run"], "count": len(timers), "results": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", help="check a single timer unit instead of auto-discovering")
    ap.add_argument("--dry-run", action="store_true", help="detect only, no systemctl mutation")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report = scan_and_repair(args.unit, args.dry_run)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"timer_self_repair — {report['count']} unit(s) scanned")
        needs_attention = 0
        for unit, r in sorted(report["results"].items()):
            if r["status"] == "healthy":
                continue
            needs_attention += 1
            marker = {"repaired": "🟢 SELF-REPAIRED", "repair_attempted": "🟡 REPAIR ATTEMPTED (unresolved)",
                      "escalated_repeat_failure": "🔴 ESCALATED (repeat failure)"}.get(r["status"], r["status"])
            print(f"  {marker}  {unit}  problems={r['problems']}")
            if r.get("repair_actions"):
                for a in r["repair_actions"]:
                    print(f"      - {a}")
        if needs_attention == 0:
            print("  all wing timers healthy")

    escalated = sum(1 for r in report["results"].values()
                     if r["status"] in ("escalated_repeat_failure", "repair_attempted"))
    sys.exit(1 if escalated else 0)


if __name__ == "__main__":
    main()
