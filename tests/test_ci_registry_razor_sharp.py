#!/usr/bin/env python3
"""
test_ci_registry_razor_sharp.py
===============================
Regression guard for MISSION-636.

Defect: razor_sharp_status compared last_verified age against
entry["currency_window_hours"] with a raw `>=`. When a designation is retired
on-demand (regent-portal-live) its currency_window_hours/reeval_cadence_days are
nulled — the raw comparison against None raised TypeError and aborted the ENTIRE
fleet sweep, leaving 46/53 designations frozen at status 'unknown' and the
razor-sharp policy engine silently non-functional.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD_DIR))

from core.ci.registry import razor_sharp_status  # noqa: E402

NOW = datetime(2026, 7, 16, tzinfo=timezone.utc)


def _fresh(**over):
    e = {
        "last_verified": (NOW - timedelta(hours=1)).isoformat(),
        "last_reeval": NOW.date().isoformat(),
        "currency_window_hours": 24,
        "reeval_cadence_days": 7,
    }
    e.update(over)
    return e


def test_retired_on_demand_does_not_crash_and_returns_retired():
    # The exact M-636 crash vector: retired entry with nulled windows.
    entry = _fresh(status="retired_on_demand",
                   currency_window_hours=None, reeval_cadence_days=None)
    assert razor_sharp_status(entry, probe_ok=True, now=NOW) == "RETIRED"


def test_null_currency_window_on_non_retired_does_not_crash():
    # Defensive: even a non-retired entry with a null window must not raise.
    entry = _fresh(currency_window_hours=None, reeval_cadence_days=None)
    # No currency/reeval clock → cannot be DULL on those axes → RAZOR_SHARP.
    assert razor_sharp_status(entry, probe_ok=True, now=NOW) == "RAZOR_SHARP"


def test_fresh_probe_ok_is_razor_sharp():
    assert razor_sharp_status(_fresh(), probe_ok=True, now=NOW) == "RAZOR_SHARP"


def test_probe_fail_is_red():
    assert razor_sharp_status(_fresh(), probe_ok=False, now=NOW) == "RED"


def test_stale_currency_is_dull():
    entry = _fresh(last_verified=(NOW - timedelta(hours=100)).isoformat())
    assert razor_sharp_status(entry, probe_ok=True, now=NOW) == "DULL"


def test_overdue_reeval_is_dull():
    entry = _fresh(last_reeval="2026-01-01")
    assert razor_sharp_status(entry, probe_ok=True, now=NOW) == "DULL"
