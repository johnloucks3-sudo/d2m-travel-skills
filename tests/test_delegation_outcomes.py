"""Regression tests for core/staffing/delegation_outcomes.py and the two
recording wrappers built on it (integrity_check.verify_and_record,
delegation_wiring.certify_mission_and_record) — SO-WING-OVERSIGHT-2026.

Hermeticity: every test redirects OUTCOME_LOG/HALE_DECISIONS to tmp_path so
none of this ever touches the real OpsCenter/delegation_outcomes.jsonl or
hale_decisions.md. Wrapper tests stub the underlying dispatch calls
(cc_integrity_double_check / certify_mission) so nothing shells out to agy/
opencode or hits the real Silver ledger.
"""
import sys
from pathlib import Path

THUNDERBIRD_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(THUNDERBIRD_DIR))

import core.staffing.delegation_outcomes as do  # noqa: E402
import core.staffing.integrity_check as integrity_check  # noqa: E402
import core.relay.delegation_wiring as wiring  # noqa: E402
import core.silver.gate as silver_gate  # noqa: E402


def _isolate_ledger(tmp_path, monkeypatch):
    outcome_log = tmp_path / "outcomes.jsonl"
    decisions = tmp_path / "decisions.md"
    monkeypatch.setattr(do, "OUTCOME_LOG", outcome_log)
    monkeypatch.setattr(do, "HALE_DECISIONS", decisions)
    # page_commander best-effort-fails against real Telegram creds anyway,
    # but stub it so tests assert on whether it was CALLED, not on network.
    pages = []
    monkeypatch.setattr(do, "page_commander",
                        lambda **kw: pages.append(kw) or True)
    return outcome_log, decisions, pages


# ── delegation_outcomes core ────────────────────────────────────────────────

def test_record_outcome_appends_and_mirrors(tmp_path, monkeypatch):
    outcome_log, decisions, _ = _isolate_ledger(tmp_path, monkeypatch)
    row = do.record_outcome(seat="AG", action="integrity_check", verdict="DISCREPANCY",
                            ticket_id="T-1", discrepancy_detail="state missing")
    assert outcome_log.exists()
    assert row["verdict"] == "DISCREPANCY"
    text = decisions.read_text()
    assert "CHIEF WING-OPS" in text and "T-1" in text and "DISCREPANCY" in text


def test_record_outcome_never_raises_on_bad_seat(tmp_path, monkeypatch):
    _isolate_ledger(tmp_path, monkeypatch)
    # unknown seat logs a warning but still records — never blocks the caller
    row = do.record_outcome(seat="ZZZ", action="delegated", verdict="PENDING", ticket_id="T-2")
    assert row["seat"] == "ZZZ"


def test_outstanding_only_returns_unreconciled_past_due(tmp_path, monkeypatch):
    _isolate_ledger(tmp_path, monkeypatch)
    do.record_outcome(seat="OC", action="delegated", verdict="PENDING", ticket_id="T-3",
                      dispatch_mode="async_poll", follow_up_due="2020-01-01T00:00:00+00:00")
    do.record_outcome(seat="OC", action="delegated", verdict="PENDING", ticket_id="T-4",
                      dispatch_mode="async_poll", follow_up_due="2099-01-01T00:00:00+00:00")
    out = do.outstanding("async_poll", older_than_hours=0)
    ids = {r["ticket_id"] for r in out}
    assert ids == {"T-3"}  # T-4 not due yet


def test_outstanding_excludes_reconciled(tmp_path, monkeypatch):
    _isolate_ledger(tmp_path, monkeypatch)
    do.record_outcome(seat="OC", action="delegated", verdict="PENDING", ticket_id="T-5",
                      dispatch_mode="async_poll", follow_up_due="2020-01-01T00:00:00+00:00")
    do.record_outcome(seat="OC", action="reconciliation", verdict="PASS", ticket_id="T-5",
                      dispatch_mode="async_poll", reconciled=True)
    out = do.outstanding("async_poll", older_than_hours=0)
    assert out == []


def test_rollup_stats_counts_categories(tmp_path, monkeypatch):
    _isolate_ledger(tmp_path, monkeypatch)
    do.record_outcome(seat="CC", action="self_executed", verdict="PASS", ticket_id="T-6",
                      routing_recommendation="OC")  # no rationale -> unjustified
    do.record_outcome(seat="AG", action="integrity_check", verdict="DISCREPANCY", ticket_id="T-7")
    do.record_outcome(seat="OC", action="certification", verdict="BLOCKED", ticket_id="T-8")
    s = do.rollup_stats(since_days=30)
    assert s["self_execute_count"] == 1
    assert s["self_execute_unjustified"] == 1
    assert s["discrepancies_caught"] == 1
    assert s["blocked_certifications"] == 1


# ── integrity_check.verify_and_record ───────────────────────────────────────

def test_verify_and_record_pass(tmp_path, monkeypatch):
    _isolate_ledger(tmp_path, monkeypatch)
    monkeypatch.setattr(integrity_check, "cc_integrity_double_check",
                        lambda *a, **k: {"ok": True, "returncode": 0, "model": "x",
                                         "stdout": "INTEGRITY: ALL-VERIFIED", "stderr": "",
                                         "deliverable_path": None, "deliverable_written": False})
    r = integrity_check.verify_and_record(["claim 1"], engine="AG", ticket_id="T-9")
    assert r["verdict"] == "PASS"
    rows = do._read_rows(do.OUTCOME_LOG)
    assert rows[0]["verdict"] == "PASS" and rows[0]["action"] == "integrity_check"


def test_verify_and_record_discrepancy_pages_commander(tmp_path, monkeypatch):
    _, _, pages = _isolate_ledger(tmp_path, monkeypatch)
    monkeypatch.setattr(integrity_check, "cc_integrity_double_check",
                        lambda *a, **k: {"ok": True, "returncode": 0, "model": "x",
                                         "stdout": "INTEGRITY: DISCREPANCIES — claim 1 wrong",
                                         "stderr": "", "deliverable_path": None,
                                         "deliverable_written": False})
    r = integrity_check.verify_and_record(["claim 1"], engine="AG", ticket_id="T-10")
    assert r["verdict"] == "DISCREPANCY"
    assert len(pages) == 1  # real-time page fired


def test_verify_and_record_unreachable_forces_unverified(tmp_path, monkeypatch):
    _, _, pages = _isolate_ledger(tmp_path, monkeypatch)
    monkeypatch.setattr(integrity_check, "cc_integrity_double_check",
                        lambda *a, **k: {"ok": False, "returncode": 127, "model": "x",
                                         "stdout": "", "stderr": "not found",
                                         "deliverable_path": None, "deliverable_written": False})
    r = integrity_check.verify_and_record(["claim 1"], engine="OC", ticket_id="T-11")
    assert r["verdict"] == "UNVERIFIED"  # never silently upgraded to PASS
    assert len(pages) == 1


# ── delegation_wiring.certify_mission_and_record ────────────────────────────

def _isolate_silver(tmp_path, monkeypatch):
    monkeypatch.setattr(silver_gate, "LEDGER", tmp_path / "silver_ledger.jsonl")
    monkeypatch.setattr(silver_gate, "DECISIONS", tmp_path / "silver_decisions.md")


def test_certify_mission_and_record_pass(tmp_path, monkeypatch):
    _isolate_ledger(tmp_path, monkeypatch)
    _isolate_silver(tmp_path, monkeypatch)
    bus_events = []
    monkeypatch.setattr(wiring, "mirror_stage_to_bus",
                        lambda *a, **k: bus_events.append(a) or {"ok": True})
    art = tmp_path / "artifact.md"
    art.write_text("3 rows confirmed")
    r = wiring.certify_mission_and_record("M-1", "OC", "CC", str(art), "3 rows confirmed")
    assert r["ok"] is True
    rows = do._read_rows(do.OUTCOME_LOG)
    assert rows[0]["verdict"] == "PASS" and rows[0]["action"] == "certification"


def test_certify_mission_and_record_self_cert_blocked_no_page(tmp_path, monkeypatch):
    _, _, pages = _isolate_ledger(tmp_path, monkeypatch)
    _isolate_silver(tmp_path, monkeypatch)
    r = wiring.certify_mission_and_record("M-2", "OC", "OC", "artifact.json", "crit")
    assert r["ok"] is False
    assert "self-certification" in r["error"]
    rows = do._read_rows(do.OUTCOME_LOG)
    assert rows[0]["verdict"] == "BLOCKED"
    assert pages == []  # routine validation error — no alert-fatigue page


def test_certify_mission_and_record_content_hold_pages(tmp_path, monkeypatch):
    _, _, pages = _isolate_ledger(tmp_path, monkeypatch)
    _isolate_silver(tmp_path, monkeypatch)
    # a bare claim (no path/@/url) fails Silver's back-gate concrete-reference check
    r = wiring.certify_mission_and_record("M-3", "OC", "CC", "trust me it works", "criteria here")
    assert r["ok"] is False
    assert "CHIEF SILVER back-gate HOLD" in r["error"]
    assert len(pages) == 1  # content-level failure — pages the Commander
