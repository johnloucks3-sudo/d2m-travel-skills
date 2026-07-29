"""Tests for Commander-answer suppression in scripts/tcd_data.py.

THE INCIDENT (2026-07-29)
`build_strategic`/`build_operational` regenerated every alert card from state
on EVERY sync, `unread: True`, with no check for whether the Commander had
already answered. tcd-sync runs ~every 10 minutes, so a close was erased on
the next tick. The silver_ledger record for alert-MCLEOD-2984034-FPD-TRIGGER:

  Jul 29 00:36  "will contact Erik McLeod re: $11,943.15 FPD directly"
  Jul 29 03:50  "FBD accomplished 20 July, 8 days ago"
  Jul 29 03:54  "FBD accomplished 20 July, 8 days ago"   (again)
  Jul 29 04:10  (card re-raised anyway)
  Jul 29 17:35  "AS I have stated many times, the final payment has been submitted"

Five answers over eighteen hours about a payment completed 20 July. Detecting a
thing repeatedly is not tracking it (MAST FM-1.3, step repetition).

The opposite failure is equally real and is tested here too: suppressing
forever would swallow a genuine recurrence. Suppression is scoped to the
alert's own trigger_date.
"""
from __future__ import annotations

import json

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path("/home/john/Thunderbird/scripts")))
import tcd_data  # noqa: E402


@pytest.fixture(autouse=True)
def clear_cache():
    tcd_data._DISMISSED_CACHE.clear()
    yield
    tcd_data._DISMISSED_CACHE.clear()


def _ledger(tmp_path, rows):
    p = tmp_path / "silver_ledger.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


def _override_row(mid, ts):
    return {"stage": "back", "mission_id": mid, "work_product": "x",
            "verdict": "OVERRIDE", "checks_run": ["human-override"],
            "holds": [], "ts": ts, "overridden_by": "Commander"}


def _close_comment_row(mid, ts):
    return {"stage": "back", "mission_id": mid,
            "work_product": "[Commander CLOSE via tcd.d2mluxury.quest] handled",
            "verdict": "HOLD", "checks_run": [], "holds": [], "ts": ts,
            "overridden_by": None}


# --------------------------------------------------------------- detection

def test_override_row_counts_as_an_answer(tmp_path):
    p = _ledger(tmp_path, [_override_row("alert-X", "2026-07-29T17:00:00+00:00")])
    assert "alert-X" in tcd_data._commander_dismissals(p)


def test_commander_close_on_a_HOLD_still_counts_as_an_answer(tmp_path):
    """The McLeod rows were HOLD verdicts carrying a Commander comment. If only
    OVERRIDE counted, the eighteen hours of answers would still be ignored."""
    p = _ledger(tmp_path, [_close_comment_row("alert-Y", "2026-07-29T03:50:00+00:00")])
    assert "alert-Y" in tcd_data._commander_dismissals(p)


def test_ordinary_gate_rows_are_not_answers(tmp_path):
    p = _ledger(tmp_path, [{"mission_id": "alert-Z", "verdict": "HOLD",
                            "work_product": "criteria not met", "ts": "2026-07-29T01:00:00+00:00"}])
    assert "alert-Z" not in tcd_data._commander_dismissals(p)


def test_latest_answer_wins(tmp_path):
    p = _ledger(tmp_path, [
        _close_comment_row("alert-A", "2026-07-29T03:50:00+00:00"),
        _override_row("alert-A", "2026-07-29T17:35:00+00:00")])
    assert tcd_data._commander_dismissals(p)["alert-A"].startswith("2026-07-29T17:35")


def test_void_annotation_cannot_silence_an_alert(tmp_path):
    """A synthetic/test override must never suppress a real Commander alert."""
    p = _ledger(tmp_path, [
        _override_row("alert-FAKE", "2026-07-29T17:42:00+00:00"),
        {"mission_id": "alert-FAKE", "verdict": "VOID", "work_product": "[ANNOTATION]",
         "holds": ["synthetic test row"], "ts": "2026-07-29T17:50:00+00:00"}])
    assert "alert-FAKE" not in tcd_data._commander_dismissals(p)


def test_missing_ledger_is_safe(tmp_path):
    assert tcd_data._commander_dismissals(tmp_path / "nope.jsonl") == {}


def test_corrupt_lines_do_not_crash_the_scan(tmp_path):
    p = tmp_path / "l.jsonl"
    p.write_text('{"bad json\n' + json.dumps(_override_row("alert-OK", "2026-07-29T10:00:00+00:00")) + "\n")
    assert "alert-OK" in tcd_data._commander_dismissals(p)


# ------------------------------------------------------------ suppression

def test_answered_alert_is_suppressed():
    d = {"alert-M": "2026-07-29T17:35:00+00:00"}
    assert tcd_data._alert_answered({"id": "M", "trigger_date": "2026-07-07T00:00:00"}, d)


def test_a_NEW_trigger_still_surfaces():
    """THE SAFETY PROPERTY. Suppressing forever would swallow a real
    recurrence -- a new deadline or changed amount must reach the Commander."""
    d = {"alert-M": "2026-07-29T17:35:00+00:00"}
    assert not tcd_data._alert_answered(
        {"id": "M", "trigger_date": "2027-01-01T00:00:00"}, d)


def test_unanswered_alert_is_not_suppressed():
    assert not tcd_data._alert_answered({"id": "NEW", "trigger_date": "2026-07-29T00:00:00"}, {})


def test_alert_with_no_trigger_date_is_suppressed_once_answered():
    d = {"alert-M": "2026-07-29T17:35:00+00:00"}
    assert tcd_data._alert_answered({"id": "M"}, d)


# ------------------------------------------------------------- end to end

def test_answered_alert_is_absent_from_the_strategic_board(monkeypatch):
    monkeypatch.setattr(tcd_data, "_commander_dismissals",
                        lambda *a, **k: {"alert-GONE": "2026-07-29T17:35:00+00:00"})
    state = {"deferred_alerts": [
        {"id": "GONE", "priority": "P1", "amount": "$24,798",
         "message": "answered already", "trigger_date": "2026-07-07T00:00:00"},
        {"id": "LIVE", "priority": "P1", "amount": "$5,000",
         "message": "never answered", "trigger_date": "2026-07-07T00:00:00"},
    ]}
    ids = {f["id"] for f in tcd_data.build_strategic(state)}
    assert "alert-GONE" not in ids
    assert "alert-LIVE" in ids


def test_suppression_applies_to_the_operational_board_too():
    """Both builders regenerate alerts; fixing only one leaves the loop open."""
    import inspect
    src = inspect.getsource(tcd_data.build_operational)
    assert "_alert_answered" in src
