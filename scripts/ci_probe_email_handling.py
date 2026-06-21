#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Email Handling (d2m → Commander delivery)
============================================================
Dreams2Memories Travel · built 2026-06-21 (Commander: "this is CI, and it is failing")

The failure this catches is the one that bit us: mail RECEIVED at d2m but never
DELIVERED to the Commander, hidden behind a "Replied" label. This probe reads
the digest courier's own ledger and goes RED on the gap — received != delivered
in the last run, OR the courier hasn't run inside its window. Delivery is the
metric, presence is not.

Exit 0 = RAZOR_SHARP, 1 = RED (gap or stale).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE = Path("/home/john/Thunderbird/OpsCenter/state/d2m_digest_state.json")
STALE_HOURS = 8


def fail(m): print(f"RED email-handling: {m}"); sys.exit(1)


def main():
    if not STATE.exists():
        fail("no digest state — courier has never run (d2m→Commander delivery unproven)")
    st = json.loads(STATE.read_text())
    runs = st.get("runs", [])
    if not runs:
        fail("courier ledger empty — no delivery run recorded")
    last = runs[-1]
    # freshness
    try:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(last["ts"])).total_seconds() / 3600
    except Exception:
        age_h = 9e9
    if age_h > STALE_HOURS:
        fail(f"stale: last courier run {age_h:.1f}h ago (window {STALE_HOURS}h) — mail may be piling up undelivered")
    # the core check: did everything received get delivered?
    gap = last.get("received", 0) - last.get("delivered", 0)
    if gap > 0:
        fail(f"DELIVERY GAP — last run received {last['received']} but delivered {last['delivered']} "
             f"({gap} actionable email(s) stuck at d2m, not sent to Commander)")
    print(f"RAZOR_SHARP email-handling: last run {age_h:.1f}h ago, "
          f"received={last.get('received')} delivered={last.get('delivered')} (no gap)")
    sys.exit(0)


if __name__ == "__main__":
    main()
