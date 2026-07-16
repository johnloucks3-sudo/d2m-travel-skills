#!/usr/bin/env python3
"""
test_backup_verify_monthly_archive.py
=====================================
Regression guard for MISSION-642.

Defect: core/ops/thunderbird_monthly_archive.py writes its state to the REPO
ROOT (monthly_archive_state.json), but core/watchtower/thunderbird_backup_verify.py
read the stale state/ copy (frozen at March 2026). The monthly timer ran fine
every month, yet the verifier falsely reported "not run since March 2026".

These tests are offline/deterministic — no timers, no Evernote, no network.
"""

import importlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

THUNDERBIRD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD_DIR))

from core.watchtower import thunderbird_backup_verify as bv  # noqa: E402


def test_monthly_state_resolves_to_repo_root_when_present():
    # The producer writes the canonical file at the repo root; the verifier must
    # prefer it over the legacy state/ copy whenever it exists.
    canon = THUNDERBIRD_DIR / "monthly_archive_state.json"
    if canon.exists():
        assert bv.MONTHLY_STATE == canon
    else:
        assert bv.MONTHLY_STATE == THUNDERBIRD_DIR / "state" / "monthly_archive_state.json"


def _write_state(path: Path, month: str):
    path.write_text(json.dumps({
        "last_archive": {"status": "success", "month": month,
                         "month_display": month, "files_count": 42}
    }))


def test_current_month_state_is_ok(tmp_path, monkeypatch):
    now = datetime.now()
    state = tmp_path / "monthly_archive_state.json"
    _write_state(state, now.strftime("%Y%m"))
    monkeypatch.setattr(bv, "MONTHLY_STATE", state)
    result = bv.check_monthly_archive()
    assert result["status"] == "OK"
    assert result["files_count"] == 42


def test_stale_month_after_the_5th_warns(tmp_path, monkeypatch):
    state = tmp_path / "monthly_archive_state.json"
    _write_state(state, "202603")  # March — the exact stale value that caused M-642

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 7, 16)

    monkeypatch.setattr(bv, "MONTHLY_STATE", state)
    monkeypatch.setattr(bv, "datetime", _FixedDatetime)
    result = bv.check_monthly_archive()
    assert result["status"] == "WARN"
