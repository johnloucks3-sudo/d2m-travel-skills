#!/usr/bin/env python3
"""
test_restart_flap_escalation.py
===============================
Offline, deterministic tests for scripts/restart_flap_detector.py::_escalate_flagged.

Guards the connector contract: a unit over its restart-flap threshold must
actually reach the existing generic_remediate._escalate() notification path,
not just sit in the detector's state file. Purely additive — the detector's
scan/count/log behavior is untouched.

Contract enforced here:
  * FLAGGED units -> _escalate() called exactly once per unit, with the unit
    name and a reason string carrying the REAL starts_24h/starts_7d numbers.
  * zero FLAGGED units -> _escalate_flagged() returns [] and _escalate() is
    never called.

Author: HALE-OC — task bb-212f2ee4
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

THUNDERBIRD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD_DIR))

from scripts.restart_flap_detector import _escalate_flagged  # noqa: E402


def _scan_result(*units):
    return {
        "scanned_at": "2026-08-11T00:00:00+00:00",
        "window_days": 7,
        "units": dict(units),
    }


def test_flagged_unit_escalated_once_with_numbers():
    result = _scan_result(
        (
            "thunderbird-telegram-gw.service",
            {
                "starts_24h": 9,
                "starts_7d": 21,
                "threshold_24h": 8,
                "threshold_7d": 20,
                "FLAGGED": True,
            },
        )
    )
    with mock.patch(
        "scripts.generic_remediate._escalate"
    ) as mock_escalate:
        escalated = _escalate_flagged(result)

    assert escalated == ["thunderbird-telegram-gw.service"]
    mock_escalate.assert_called_once()
    unit, reason = mock_escalate.call_args.args
    assert unit == "thunderbird-telegram-gw.service"
    assert "9 starts/24h" in reason
    assert "21 starts/7d" in reason


def test_no_flagged_units_returns_empty_and_no_escalation():
    result = _scan_result(
        (
            "d2m-fare-watch.service",
            {
                "starts_24h": 1,
                "starts_7d": 3,
                "threshold_24h": 6,
                "threshold_7d": 15,
                "FLAGGED": False,
            },
        )
    )
    with mock.patch(
        "scripts.generic_remediate._escalate"
    ) as mock_escalate:
        escalated = _escalate_flagged(result)

    assert escalated == []
    mock_escalate.assert_not_called()
