#!/usr/bin/env python3
"""
cc_overflow_watcher.py — Auto-route CC to OC when Claude weekly usage hits threshold.

Reads usage_ledger.json (populated by update_usage.py from the MAX plan screen).
Writes .cc_overflow_mode flag file when weekly_all_pct >= THRESHOLD.
tb / pa in provider_switch.sh check this flag before launching claude.

Usage:
    python3 scripts/cc_overflow_watcher.py          # check and update flag
    python3 scripts/cc_overflow_watcher.py --status # show current state
    python3 scripts/cc_overflow_watcher.py --clear  # force-clear flag (go direct)
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

TB = Path("/home/john/Thunderbird")
LEDGER = TB / "OpsCenter" / "usage_ledger.json"
FLAG = TB / ".cc_overflow_mode"

THRESHOLD = 75        # % weekly usage → switch to overflow
OVERFLOW_MODEL = "opencode/deepseek-v4-flash-free"   # Zen free tier — zero Poe points
OVERFLOW_LABEL = "DeepSeek V4 Flash (Zen free) — CC overflow to OC"

def latest_snapshot():
    try:
        d = json.loads(LEDGER.read_text())
        snaps = d.get("manual_snapshots", [])
        return snaps[-1] if snaps else None
    except Exception:
        return None

def read_flag():
    try:
        return json.loads(FLAG.read_text())
    except Exception:
        return None

def write_flag(pct, model, label):
    FLAG.write_text(json.dumps({
        "active": True,
        "weekly_pct": pct,
        "model": model,
        "label": label,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }))

def clear_flag():
    FLAG.unlink(missing_ok=True)

def check(verbose=True):
    snap = latest_snapshot()
    if snap is None:
        if verbose:
            print("⚠  No usage snapshot found — run: update_usage.py <wkly%> <sonnet%> <runs_used> <runs_total>")
        return

    pct = snap.get("weekly_all_pct", 0)
    age = ""
    try:
        ts = datetime.fromisoformat(snap["ts"])
        mins = int((datetime.now(timezone.utc) - ts).total_seconds() / 60)
        age = f"  (snapshot {mins}m ago)"
    except Exception:
        pass

    current_flag = read_flag()

    if pct >= THRESHOLD:
        write_flag(pct, OVERFLOW_MODEL, OVERFLOW_LABEL)
        if verbose:
            print(f"🔴 {pct}% weekly — OVERFLOW ACTIVE → {OVERFLOW_MODEL}{age}")
            print(f"   New 'claude' sessions will route through gateway to {OVERFLOW_LABEL}")
            print(f"   Override: run 'pa' explicitly to go Anthropic direct")
    else:
        if current_flag and current_flag.get("active"):
            clear_flag()
            if verbose:
                print(f"✅ {pct}% weekly — below threshold, overflow cleared{age}")
        else:
            if verbose:
                print(f"✅ {pct}% weekly — Anthropic direct (threshold: {THRESHOLD}%){age}")

def status():
    snap = latest_snapshot()
    flag = read_flag()
    pct = snap.get("weekly_all_pct", "?") if snap else "?"
    print(f"Weekly usage : {pct}%  (threshold: {THRESHOLD}%)")
    print(f"Overflow flag: {'ACTIVE → ' + flag['model'] if flag and flag.get('active') else 'clear'}")
    if flag:
        print(f"Triggered at : {flag.get('triggered_at','?')[:16]}")

if __name__ == "__main__":
    if "--status" in sys.argv:
        status()
    elif "--clear" in sys.argv:
        clear_flag()
        print("✅ Overflow flag cleared — next session goes Anthropic direct")
    else:
        check()
