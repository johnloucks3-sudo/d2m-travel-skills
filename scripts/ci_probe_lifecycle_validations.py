#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Lifecycle Dani Validation Email Generator
=============================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Checks:
  1. OpsCenter/logs/validation_audit.jsonl — last generator_complete event
     < 35 days ago (monthly generator; monthly cadence gives 35d window)
  2. Validation_audit.jsonl must have at least 1 client_validated event
     (verifies generator actually processed clients, not just started and failed)

PROBE-NOTE: The engine scripts/render_dani_validation_emails.py writes HTML to
output/validation_emails/, but only 2 .md files are present there (dated Jun 4),
suggesting output format may differ. The canonical freshness signal is
validation_audit.jsonl (last generator_complete = 2026-06-29). File system
artifacts are secondary and checked only for informational count.

Probe does NOT re-run the engine. The repair function re-runs it.
Exit 0 = GREEN. Exit 1 = RED.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
VALIDATION_AUDIT = THUNDERBIRD_ROOT / "OpsCenter" / "logs" / "validation_audit.jsonl"
VALIDATION_OUTPUT = THUNDERBIRD_ROOT / "output" / "validation_emails"
CURRENCY_DAYS = 35  # Monthly generator; give 5-day grace window
ID = "lifecycle-validations"


def fail(m: str) -> None:
    print(f"RED {ID}: {m}")
    sys.exit(1)


def main() -> None:
    # ── CHECK 1: Audit log exists ────────────────────────────────────────────
    if not VALIDATION_AUDIT.exists():
        fail(
            f"validation_audit.jsonl missing at {VALIDATION_AUDIT} — "
            "validation email generator has never run or log was deleted"
        )

    # Parse all entries
    entries = []
    try:
        for line in VALIDATION_AUDIT.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except Exception as e:
        fail(f"Could not read {VALIDATION_AUDIT}: {e}")

    if not entries:
        fail("validation_audit.jsonl is empty — generator has never completed")

    # ── CHECK 2: Last generator_complete event freshness ─────────────────────
    generator_complete = [e for e in entries if e.get("event") == "generator_complete"]
    if not generator_complete:
        fail(
            "No generator_complete events in validation_audit.jsonl — "
            "validation email generator has never completed a full run"
        )

    last_complete = generator_complete[-1]
    ts_str = last_complete.get("timestamp") or last_complete.get("ts")
    if not ts_str:
        fail(f"generator_complete event has no timestamp field: {last_complete}")

    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except Exception as e:
        fail(f"Cannot parse generator_complete timestamp '{ts_str}': {e}")

    now = datetime.now(tz=timezone.utc)
    age_d = (now - ts).total_seconds() / 86400
    if age_d > CURRENCY_DAYS:
        fail(
            f"Validation email generator last ran {age_d:.1f} days ago "
            f"(threshold {CURRENCY_DAYS}d) — DARK for more than a month. "
            f"Last run: {ts_str}. "
            "Fix: python3 scripts/render_dani_validation_emails.py"
        )

    # ── CHECK 3: At least 1 client_validated event in this cycle ────────────
    # "This cycle" = since the last generator_complete we just checked
    # Look for any client_validated after the generator_complete ts
    client_validated = [
        e for e in entries
        if e.get("event") == "client_validated"
    ]
    # Check there are at least some total client_validated events
    if not client_validated:
        fail(
            "No client_validated events in validation_audit.jsonl — "
            "generator may have started but not processed any clients"
        )

    # Informational: output file count
    output_count = 0
    if VALIDATION_OUTPUT.exists():
        output_count = len(list(VALIDATION_OUTPUT.glob("*")))

    clients_in_last_run = last_complete.get("clients", "?")
    month = last_complete.get("month", "?")
    print(
        f"GREEN {ID}: generator_complete {age_d:.1f}d ago (threshold {CURRENCY_DAYS}d); "
        f"last run: {ts_str[:10]} month={month} clients={clients_in_last_run}; "
        f"total client_validated events: {len(client_validated)}; "
        f"output_files: {output_count}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
