#!/usr/bin/env python3
"""
FPD Sentinel — Final Payment Date State Machine
================================================
Dreams2Memories Travel, LLC | scripts/fpd_sentinel.py

Tracks FPD state per client across brief cycles so the morning brief
does not re-flag stale items. State machine:

    OPEN     — FPD exists, not yet overdue
    OVERDUE  — Past due; flagged once, then enters 30-day watch section
    RECEIVED — Payment confirmed; never re-flags
    SILENT   — Manually suppressed (set via --silence CLIENT)

State persists in OpsCenter/state/fpd_state.json.

Usage:
    python3 scripts/fpd_sentinel.py --sync          # Sync state from dossiers, print report
    python3 scripts/fpd_sentinel.py --report        # Print current state (no sync)
    python3 scripts/fpd_sentinel.py --mark-received CLIENT  # Mark client RECEIVED
    python3 scripts/fpd_sentinel.py --silence CLIENT        # Move client to SILENT
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))

STATE_PATH = THUNDERBIRD / "OpsCenter" / "state" / "fpd_state.json"

# State constants
STATE_OPEN = "OPEN"
STATE_OVERDUE = "OVERDUE"
STATE_RECEIVED = "RECEIVED"
STATE_SILENT = "SILENT"

# After first OVERDUE flag, move to 30-day watch (re-flag every 30 days)
OVERDUE_RECHECK_DAYS = 30


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Dossier reader — pulls client key + FPD + payment_status
# ---------------------------------------------------------------------------

def _read_dossiers() -> list[dict]:
    """Scan dossier directory for FPD metadata via YAML frontmatter."""
    import re
    try:
        import yaml
    except ImportError:
        yaml = None

    dossier_dir = THUNDERBIRD / "dossiers"
    SKIP = {"CLAUDE.md", "DOSSIER_Regent_Tips_Guide.md"}
    records = []

    for f in sorted(dossier_dir.glob("*.md")):
        if f.name in SKIP:
            continue
        try:
            text = f.read_text(encoding="utf-8")
            meta = {}
            m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if m and yaml:
                meta = yaml.safe_load(m.group(1)) or {}
            elif m:
                # Minimal YAML parse without library
                for line in m.group(1).splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()

            client_key = meta.get("client_key") or meta.get("full_name") or f.stem
            fpd_raw = meta.get("fpd") or meta.get("final_payment_date") or meta.get("final_payment")
            payment_status = meta.get("payment_status", "").lower()

            fpd_date = None
            if fpd_raw:
                for fmt in ("%Y-%m-%d", "%d %b %Y", "%-d %b %Y", "%B %d, %Y"):
                    try:
                        fpd_date = datetime.strptime(str(fpd_raw).strip(), fmt).date()
                        break
                    except ValueError:
                        continue

            if fpd_date or payment_status in ("paid", "paid_in_full", "complete"):
                records.append({
                    "client_key": str(client_key),
                    "dossier": f.name,
                    "fpd": fpd_date,
                    "payment_status": payment_status,
                })
        except Exception:
            continue

    return records


# ---------------------------------------------------------------------------
# State sync logic
# ---------------------------------------------------------------------------

def sync_state() -> dict:
    """Read dossiers, update state machine, return updated state."""
    today = date.today()
    state = _load_state()

    dossier_records = _read_dossiers()

    for rec in dossier_records:
        key = rec["client_key"]
        existing = state.get(key, {})
        current_status = existing.get("status", STATE_OPEN)

        # RECEIVED / SILENT are terminal — never downgrade
        if current_status in (STATE_RECEIVED, STATE_SILENT):
            # But check if payment_status changed to received in dossier
            if rec["payment_status"] in ("paid", "paid_in_full", "complete"):
                state[key] = {
                    **existing,
                    "status": STATE_RECEIVED,
                    "payment_status": rec["payment_status"],
                    "updated_at": today.isoformat(),
                }
            continue

        # Payment confirmed in dossier — upgrade to RECEIVED
        if rec["payment_status"] in ("paid", "paid_in_full", "complete"):
            state[key] = {
                "status": STATE_RECEIVED,
                "fpd": str(rec["fpd"]) if rec["fpd"] else None,
                "payment_status": rec["payment_status"],
                "dossier": rec["dossier"],
                "first_seen": existing.get("first_seen", today.isoformat()),
                "updated_at": today.isoformat(),
            }
            continue

        if rec["fpd"] is None:
            # No FPD — skip
            continue

        days_overdue = (today - rec["fpd"]).days

        if days_overdue < 0:
            # Not yet overdue
            new_status = STATE_OPEN
        else:
            # Overdue — check if we need to re-flag
            last_flagged = existing.get("last_flagged_at")
            if current_status == STATE_OVERDUE and last_flagged:
                days_since_flag = (today - date.fromisoformat(last_flagged)).days
                if days_since_flag < OVERDUE_RECHECK_DAYS:
                    # Already flagged recently — hold in watch mode
                    new_status = STATE_OVERDUE
                else:
                    # Re-flag after 30-day watch window
                    new_status = STATE_OVERDUE
                    existing["last_flagged_at"] = today.isoformat()
                    existing["flag_count"] = existing.get("flag_count", 1) + 1
            else:
                new_status = STATE_OVERDUE
                existing["last_flagged_at"] = today.isoformat()
                existing["flag_count"] = existing.get("flag_count", 0) + 1

        state[key] = {
            **existing,
            "status": new_status,
            "fpd": str(rec["fpd"]),
            "payment_status": rec["payment_status"],
            "dossier": rec["dossier"],
            "days_overdue": days_overdue if days_overdue >= 0 else 0,
            "first_seen": existing.get("first_seen", today.isoformat()),
            "updated_at": today.isoformat(),
        }

    _save_state(state)
    return state


# ---------------------------------------------------------------------------
# FPD brief helper — used by morning_brief_engine.py
# ---------------------------------------------------------------------------

def get_fpd_brief_rows(state: dict | None = None) -> dict:
    """
    Returns categorized FPD rows for brief integration.

    Returns:
        {
            "today_flags": [{"client": ..., "days_overdue": ..., "fpd": ...}],
            "watch_items": [{"client": ..., "days_overdue": ..., "last_flagged": ...}],
            "received": [{"client": ...}],
        }
    """
    if state is None:
        state = _load_state()

    today = date.today()
    today_flags = []
    watch_items = []
    received = []

    for client_key, entry in state.items():
        status = entry.get("status", STATE_OPEN)
        if status == STATE_RECEIVED:
            received.append({"client": client_key})
        elif status == STATE_OVERDUE:
            last_flagged = entry.get("last_flagged_at")
            flag_count = entry.get("flag_count", 1)
            days_since_flag = 0
            if last_flagged:
                days_since_flag = (today - date.fromisoformat(last_flagged)).days

            row = {
                "client": client_key,
                "fpd": entry.get("fpd", "?"),
                "days_overdue": entry.get("days_overdue", 0),
                "flag_count": flag_count,
                "last_flagged": last_flagged,
            }

            # First flag or re-flag day -> goes in TODAY section
            if flag_count == 1 or days_since_flag == 0:
                today_flags.append(row)
            else:
                # Subsequent days within 30-day window -> WATCH section
                watch_items.append(row)

    return {
        "today_flags": sorted(today_flags, key=lambda x: x.get("days_overdue", 0), reverse=True),
        "watch_items": sorted(watch_items, key=lambda x: x.get("days_overdue", 0), reverse=True),
        "received": received,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_report(state: dict) -> None:
    print(f"\nFPD Sentinel State — {date.today().isoformat()}")
    print("=" * 60)
    by_status: dict[str, list] = {STATE_OPEN: [], STATE_OVERDUE: [], STATE_RECEIVED: [], STATE_SILENT: []}
    for k, v in state.items():
        s = v.get("status", STATE_OPEN)
        by_status.setdefault(s, []).append((k, v))

    for status in (STATE_OVERDUE, STATE_OPEN, STATE_RECEIVED, STATE_SILENT):
        entries = by_status.get(status, [])
        if not entries:
            continue
        print(f"\n  [{status}]")
        for k, v in entries:
            fpd = v.get("fpd", "?")
            days = v.get("days_overdue", 0)
            flags = v.get("flag_count", 0)
            print(f"    {k:40s} FPD={fpd}  overdue={days}d  flags={flags}")


def main() -> None:
    p = argparse.ArgumentParser(description="FPD Sentinel — state machine for final payment dates")
    p.add_argument("--sync", action="store_true", help="Sync state from dossiers")
    p.add_argument("--report", action="store_true", help="Print current state")
    p.add_argument("--mark-received", metavar="CLIENT", help="Mark client as RECEIVED")
    p.add_argument("--silence", metavar="CLIENT", help="Move client to SILENT")
    args = p.parse_args()

    if args.mark_received:
        state = _load_state()
        key = args.mark_received
        state[key] = {
            **state.get(key, {}),
            "status": STATE_RECEIVED,
            "updated_at": date.today().isoformat(),
        }
        _save_state(state)
        print(f"Marked {key} as RECEIVED.")
        return

    if args.silence:
        state = _load_state()
        key = args.silence
        state[key] = {
            **state.get(key, {}),
            "status": STATE_SILENT,
            "updated_at": date.today().isoformat(),
        }
        _save_state(state)
        print(f"Silenced {key}.")
        return

    if args.sync:
        state = sync_state()
        _print_report(state)
        return

    if args.report:
        state = _load_state()
        _print_report(state)
        return

    # Default: sync + report
    state = sync_state()
    _print_report(state)


if __name__ == "__main__":
    main()
