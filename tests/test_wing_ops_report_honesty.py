"""Regression tests for core/ops/wing_ops_report.py — the silence-is-not-green bug.

Until 2026-07-29 this section mailed the Commander a green
"no discrepancies, blocks, or drops this window ✅" in BOTH daily briefs
whenever no failures were recorded — including when nothing had been recorded
at all. With a 4-row ledger that meant it was green by construction.

These tests are the tripwire. If a future refactor reintroduces green-on-empty,
they fail. This is the single highest-consequence bug found in the 2026-07-29
oversight review, because unlike a missing feature it actively misinforms the
one human responsible for catching everything else.
"""
from __future__ import annotations

import pytest

from core.ops import wing_ops_report as wor


def _digest(stats: dict) -> dict:
    return {"since_hours": 24, "stats": stats, "scorecard": {}, "budgets": {}}


EMPTY_LEDGER = {
    "since_days": 1, "total": 0,
    "by_seat": {"CC": 0, "OC": 0, "AG": 0},
    "self_execute_count": 0, "delegate_count": 0, "self_execute_unjustified": 0,
    "verified_pass": 0, "discrepancies_caught": 0, "unverified": 0,
    "blocked_certifications": 0, "certified_pass": 0,
    "unreconciled_oc": 0, "follow_up_overdue": 0, "dropped": 0,
}


def test_empty_ledger_does_not_render_green(monkeypatch):
    """THE BUG. Zero checks must never read as a clean window."""
    monkeypatch.setattr(wor, "reaper_is_healthy", lambda *a, **k: (True, ""),
                        raising=False)
    html = wor.build_wing_ops_section(_digest(EMPTY_LEDGER))
    assert "no discrepancies, blocks, or drops" not in html
    assert "NOTHING WAS CHECKED" in html
    assert "not a clean bill of health" in html


def test_empty_ledger_uses_warning_colour_not_success_colour():
    html = wor.build_wing_ops_section(_digest(EMPTY_LEDGER))
    assert "#16a34a" not in html.split("Per-seat budget")[0]  # no green in the verdict line


def test_clean_window_with_real_checks_does_render_green():
    """The honest green: failures were possible and none occurred."""
    stats = {**EMPTY_LEDGER, "total": 12, "verified_pass": 12}
    html = wor.build_wing_ops_section(_digest(stats))
    assert "no discrepancies, blocks, or drops across 12 checked outcome(s)" in html
    assert "NOTHING WAS CHECKED" not in html


def test_green_line_always_states_its_denominator():
    """A count without a denominator is the failure mode itself."""
    stats = {**EMPTY_LEDGER, "total": 7, "verified_pass": 7}
    html = wor.build_wing_ops_section(_digest(stats))
    assert "7 checked outcome(s)" in html


def test_real_failures_still_surface_over_everything():
    stats = {**EMPTY_LEDGER, "total": 5, "discrepancies_caught": 2}
    html = wor.build_wing_ops_section(_digest(stats))
    assert "2 discrepancy(ies) caught" in html
    assert "NOTHING WAS CHECKED" not in html


def test_degraded_oversight_layer_overrides_a_clean_line(monkeypatch):
    """If the reaper has stopped, every clean claim below it is unsupported."""
    import core.oversight.reaper as rp
    monkeypatch.setattr(rp, "reaper_is_healthy",
                        lambda *a, **k: (False, "reaper has NEVER run — OVERSIGHT NOT RUNNING"))
    stats = {**EMPTY_LEDGER, "total": 9, "verified_pass": 9}
    html = wor.build_wing_ops_section(_digest(stats))
    assert "OVERSIGHT LAYER DEGRADED" in html
    assert "OVERSIGHT NOT RUNNING" in html


def test_healthy_oversight_layer_adds_no_noise(monkeypatch):
    import core.oversight.reaper as rp
    monkeypatch.setattr(rp, "reaper_is_healthy", lambda *a, **k: (True, "ok"))
    stats = {**EMPTY_LEDGER, "total": 3, "verified_pass": 3}
    html = wor.build_wing_ops_section(_digest(stats))
    assert "OVERSIGHT LAYER DEGRADED" not in html


def test_missing_stats_still_returns_unavailable_notice():
    html = wor.build_wing_ops_section({"since_hours": 24, "stats": {}})
    assert "unavailable" in html


# ------------------------------------------------- backlog surfacing (v2)

def test_agent_stalls_and_commander_queue_are_never_collapsed():
    """Collapsing these would let the Wing's own dropped work hide inside the
    Commander's review queue, or blame him for work agents abandoned."""
    d = _digest({**EMPTY_LEDGER, "total": 5})
    d["backlog"] = {"agent_stalled": 51, "awaiting_commander": 69,
                    "agent_oldest_days": 13.2, "commander_oldest_days": 15.5}
    html = wor.build_wing_ops_section(d)
    assert "51 mission(s) stalled agent-side" in html
    assert "69 awaiting Commander" in html


def test_stale_backlog_breaks_an_otherwise_green_line():
    """A window with no discrepancies but 51 abandoned missions is not clean."""
    d = _digest({**EMPTY_LEDGER, "total": 5, "verified_pass": 5})
    d["backlog"] = {"agent_stalled": 51, "awaiting_commander": 0,
                    "agent_oldest_days": 13.2, "commander_oldest_days": 0}
    html = wor.build_wing_ops_section(d)
    assert "no discrepancies, blocks, or drops across" not in html


def test_no_backlog_leaves_green_intact():
    d = _digest({**EMPTY_LEDGER, "total": 5, "verified_pass": 5})
    d["backlog"] = {"agent_stalled": 0, "awaiting_commander": 0,
                    "agent_oldest_days": 0, "commander_oldest_days": 0}
    html = wor.build_wing_ops_section(d)
    assert "no discrepancies, blocks, or drops across 5 checked outcome(s)" in html


def test_renderer_is_pure_and_does_not_read_the_live_board(monkeypatch):
    """Regression: the renderer briefly reached out to mission_board.json,
    making it non-deterministic and untestable. Data gathering belongs in
    build_wing_ops_digest()."""
    import core.oversight.reaper as rp
    monkeypatch.setattr(rp, "stale_missions",
                        lambda **kw: (_ for _ in ()).throw(
                            AssertionError("renderer must not scan the board")))
    html = wor.build_wing_ops_section(_digest({**EMPTY_LEDGER, "total": 2}))
    assert html
