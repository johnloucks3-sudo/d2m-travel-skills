#!/usr/bin/env python3
"""
CLIENT-SEND GATE TRIPWIRE — the master-arm warning light
========================================================
Dreams2Memories Travel · built 2026-06-21 (Sterling STAFF COMMENT, CAUTION 1)

While all wing protections are lifted (`.protections_lifted`), the ONE gate the
Commander kept — client-send — is enforced by *editable code*. An autonomous
agent doing "modernization" could comment out the gate and no alarm would fire
until a client email went out. This is the missing caution light on the one
switch we can't afford to have moved silently.

This hashes the client-send enforcement path against a known-good baseline.
  - First run (no baseline): writes the baseline, exits 0.
  - Match: exit 0 (RAZOR_SHARP).
  - Mismatch / missing file: exit 1 (RED) listing exactly what changed — the
    standing order is: freeze adoption + page on RED. The baseline is rebaselined
    only by an authorized human (review the diff, then run with --rebaseline).

Wire into the daily CI routine; RED → page Commander (the gate is client-affecting).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
BASELINE = ROOT / "config" / "client_send_gate_baseline.json"

# The client-send enforcement path (Sterling's verified list).
GATE_PATH = [
    "core/policy/wing_policy.py",                 # check_draft_send / check_relay_action
    "core/email/thunderbird_commander_inbox.py",  # Tier-2 WF-17 branch (~line 1130)
    "OpsCenter/run_commander_directive_sweep.py",
    "OpsCenter/dispatch_and_email.py",
    "OpsCenter/email_task_ingest.py",
    "OpsCenter/relay_send.py",
    "core/relay/wing_relay.py",
]


def _hash(rel: str) -> str | None:
    p = ROOT / rel
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def current() -> dict:
    return {rel: _hash(rel) for rel in GATE_PATH}


def write_baseline(note: str = "") -> None:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps({"hashes": current(), "note": note}, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebaseline", action="store_true",
                    help="authorized human: accept current state as the new known-good")
    args = ap.parse_args()

    if args.rebaseline or not BASELINE.exists():
        write_baseline("rebaseline" if args.rebaseline else "initial baseline")
        print(f"BASELINE WRITTEN ({len(GATE_PATH)} files) → {BASELINE}")
        return 0

    base = json.loads(BASELINE.read_text()).get("hashes", {})
    cur = current()
    changed, missing = [], []
    for rel in GATE_PATH:
        if cur[rel] is None:
            missing.append(rel)
        elif base.get(rel) != cur[rel]:
            changed.append(rel)

    if missing or changed:
        if missing:
            print("RED client-send-gate: MISSING gate file(s) — " + ", ".join(missing))
        if changed:
            print("RED client-send-gate: gate code CHANGED since baseline — " + ", ".join(changed))
        print("  → FREEZE ADOPTION + page Commander. Review the diff; if authorized, "
              "rerun with --rebaseline.")
        return 1

    print(f"RAZOR_SHARP client-send-gate: all {len(GATE_PATH)} enforcement files match baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
