#!/usr/bin/env python3
"""
Unit tests for thunderbird_coo_watchdog.py + thunderbird_coo_escalation.py

Run: cd /home/john/Thunderbird && python3 -m pytest OpsCenter/test_coo_watchdog.py -v
"""

import json
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import thunderbird_coo_watchdog as wdog
import thunderbird_coo_escalation as esc


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _tmp_paths(tmp_path, monkeypatch):
    """Redirect file paths to temp dirs so tests don't touch production state."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    monkeypatch.setattr(wdog, "STATE_FILE", state_dir / "watchdog_state.json")
    monkeypatch.setattr(wdog, "LOG_FILE",   log_dir / "coo_watchdog.log")

    esc_log = log_dir / "coo_watchdog_escalations.log"
    monkeypatch.setattr(esc, "LOG_FILE", esc_log)

    # Reset escalation dedup state between tests
    esc._dedup_state.clear()

    yield tmp_path


@pytest.fixture()
def clean_state():
    return {
        "timestamp": None,
        "services": {},
        "last_failure_restart_times": {},
    }


# ─── Test 1: Tier 1 failure — diagnostics collected correctly ────────────────

class TestTier1DiagnosticsCollection:
    """Mock a Tier 1 service failure; verify diagnostics are collected."""

    def _make_scan_with_tier1_failure(self, svc_name="hale-draft-engine"):
        """Build a synthetic scan dict with one Tier 1 service marked failed."""
        scan = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tier1": {},
            "tier2": {},
            "tier1_failures": [svc_name],
            "tier2_failures": [],
            "all_clear": False,
        }
        for svc in wdog.TIER1_SERVICES:
            scan["tier1"][svc] = {
                "name": svc,
                "active": svc != svc_name,
                "status": "failed" if svc == svc_name else "active",
                "detail": "ExecMainStatus=1" if svc == svc_name else "",
                "timer_ok": True,
            }
        for svc in wdog.TIER2_SERVICES:
            scan["tier2"][svc] = {
                "name": svc, "active": True, "status": "active", "detail": "",
            }
        return scan

    def test_diagnostics_contain_service_name(self):
        target = "hale-draft-engine"

        # Mock _run to return realistic fake output
        fake_status = "● hale-draft-engine.service - FAILED\n   Loaded: loaded\n   Active: failed"
        fake_journal = "May 03 10:00:01 yoga hale-draft-engine[1234]: ImportError: No module named 'x'"

        with patch.object(wdog, "_run") as mock_run:
            mock_run.return_value = (1, fake_status)
            diag = wdog.run_diagnostics(target, "service failed")

        assert target in diag
        assert "DIAGNOSTICS" in diag
        assert "systemctl status" in diag

    def test_tier1_failure_triggers_diagnostics_in_cycle(self, tmp_path, monkeypatch):
        """Full cycle: Tier 1 service failure → diagnostics function called."""
        target = "hale-draft-engine"
        scan = self._make_scan_with_tier1_failure(target)

        diagnostics_called_for = []

        def fake_run_health_scan():
            return scan

        def fake_run_diagnostics(service, reason):
            diagnostics_called_for.append(service)
            return f"=== DIAGNOSTICS: {service} ==="

        def fake_attempt_recovery(service, restart_times):
            return False, restart_times

        with (
            patch.object(wdog, "run_health_scan", fake_run_health_scan),
            patch.object(wdog, "run_diagnostics", fake_run_diagnostics),
            patch.object(wdog, "attempt_recovery", fake_attempt_recovery),
            patch.object(wdog, "send_unrecoverable_alert"),
            patch.object(wdog, "load_previous_state", return_value={
                "timestamp": None, "services": {}, "last_failure_restart_times": {}
            }),
            patch.object(wdog, "save_state"),
        ):
            wdog.run_watchdog_cycle()

        assert target in diagnostics_called_for, (
            f"Expected diagnostics to be collected for {target}, got: {diagnostics_called_for}"
        )

    def test_tier1_port_diagnostic_included_for_mcp(self):
        """d2m-mcp has a port in SERVICE_PORTS — verify port check runs."""
        svc = "d2m-mcp"
        assert svc in wdog.SERVICE_PORTS, "d2m-mcp must be in SERVICE_PORTS for this test"

        fake_netstat = "tcp  0  0 0.0.0.0:8765  0.0.0.0:*  LISTEN"
        call_log = []

        def fake_run(cmd, timeout=15):
            call_log.append(cmd)
            if "netstat" in cmd:
                return 0, fake_netstat
            return 1, "fake output"

        with patch.object(wdog, "_run", fake_run):
            diag = wdog.run_diagnostics(svc, "service failed")

        netstat_calls = [c for c in call_log if "netstat" in c]
        assert netstat_calls, "Expected netstat to be called for mcp service"
        assert "8765" in diag or "port" in diag.lower()


# ─── Test 2: Tier 2 failure — state delta detection ──────────────────────────

class TestTier2StateDeltaDetection:
    """Mock a Tier 2 service failure; verify state delta is produced."""

    def _make_scan_with_tier2_failure(self, svc_name="thunderbird-fare-watch"):
        scan = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tier1": {},
            "tier2": {},
            "tier1_failures": [],
            "tier2_failures": [svc_name],
            "all_clear": False,
        }
        for svc in wdog.TIER1_SERVICES:
            scan["tier1"][svc] = {
                "name": svc, "active": True, "status": "active",
                "detail": "", "timer_ok": True,
            }
        for svc in wdog.TIER2_SERVICES:
            scan["tier2"][svc] = {
                "name": svc,
                "active": svc != svc_name,
                "status": "failed" if svc == svc_name else "active",
                "detail": "",
            }
        return scan

    def test_new_tier2_failure_produces_delta(self):
        target = "thunderbird-fare-watch"
        scan = self._make_scan_with_tier2_failure(target)

        prev_state = {
            "timestamp": None,
            "services": {},  # no prior knowledge → "new" delta
            "last_failure_restart_times": {},
        }

        deltas = wdog.compare_states(prev_state, scan)
        failed_deltas = [d for d in deltas if d["service"] == target]

        assert failed_deltas, f"Expected a delta for {target}, got: {deltas}"
        assert failed_deltas[0]["direction"] == "new"
        assert failed_deltas[0]["curr_status"] == "failed"

    def test_existing_tier2_failure_no_delta(self):
        """If service was already failed in previous state, no new delta."""
        target = "thunderbird-fare-watch"
        scan = self._make_scan_with_tier2_failure(target)

        prev_state = {
            "timestamp": None,
            "services": {target: "failed"},
            "last_failure_restart_times": {},
        }

        deltas = wdog.compare_states(prev_state, scan)
        failed_deltas = [d for d in deltas if d["service"] == target]

        assert not failed_deltas, (
            f"No delta expected for already-known failure, got: {failed_deltas}"
        )

    def test_tier2_failure_does_not_alert_commander(self):
        """Tier 2 failures must NOT call send_unrecoverable_alert."""
        target = "thunderbird-fare-watch"
        scan = self._make_scan_with_tier2_failure(target)

        with (
            patch.object(wdog, "run_health_scan", return_value=scan),
            patch.object(wdog, "load_previous_state", return_value={
                "timestamp": None, "services": {}, "last_failure_restart_times": {}
            }),
            patch.object(wdog, "run_diagnostics", return_value="fake diag"),
            patch.object(wdog, "attempt_recovery", return_value=(False, {})),
            patch.object(wdog, "save_state"),
            patch.object(wdog, "send_unrecoverable_alert") as mock_alert,
        ):
            wdog.run_watchdog_cycle()

        mock_alert.assert_not_called()


# ─── Test 3: State comparison — OK→FAIL and FAIL→OK transitions ─────────────

class TestStateComparison:
    """Verify compare_states correctly identifies degradation and recovery."""

    def _make_minimal_scan(self, service_statuses: dict) -> dict:
        """Build a scan where specified services have given statuses."""
        scan = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tier1": {},
            "tier2": {},
            "tier1_failures": [],
            "tier2_failures": [],
            "all_clear": True,
        }
        for svc in wdog.TIER1_SERVICES:
            status = service_statuses.get(svc, "active")
            is_healthy = status not in ("failed",)
            scan["tier1"][svc] = {
                "name": svc, "active": is_healthy, "status": status,
                "detail": "", "timer_ok": True,
            }
            if status == "failed":
                scan["tier1_failures"].append(svc)
                scan["all_clear"] = False

        for svc in wdog.TIER2_SERVICES:
            status = service_statuses.get(svc, "active")
            is_healthy = status not in ("failed",)
            scan["tier2"][svc] = {
                "name": svc, "active": is_healthy, "status": status, "detail": "",
            }
            if status == "failed":
                scan["tier2_failures"].append(svc)
                scan["all_clear"] = False

        return scan

    def test_ok_to_fail_transition(self):
        svc = "d2m-mcp"
        prev_state = {"services": {svc: "active"}, "last_failure_restart_times": {}}
        curr_scan = self._make_minimal_scan({svc: "failed"})

        deltas = wdog.compare_states(prev_state, curr_scan)
        match = [d for d in deltas if d["service"] == svc]

        assert match, f"Expected degraded delta for {svc}"
        assert match[0]["direction"] == "degraded"
        assert match[0]["prev_status"] == "active"
        assert match[0]["curr_status"] == "failed"

    def test_fail_to_ok_transition(self):
        svc = "d2m-mcp"
        prev_state = {"services": {svc: "failed"}, "last_failure_restart_times": {}}
        curr_scan = self._make_minimal_scan({svc: "active"})

        deltas = wdog.compare_states(prev_state, curr_scan)
        match = [d for d in deltas if d["service"] == svc]

        assert match, f"Expected recovered delta for {svc}"
        assert match[0]["direction"] == "recovered"
        assert match[0]["prev_status"] == "failed"
        assert match[0]["curr_status"] == "active"

    def test_stable_ok_produces_no_delta(self):
        svc = "d2m-mcp"
        prev_state = {"services": {svc: "active"}, "last_failure_restart_times": {}}
        curr_scan = self._make_minimal_scan({svc: "active"})

        deltas = wdog.compare_states(prev_state, curr_scan)
        match = [d for d in deltas if d["service"] == svc]

        assert not match, f"No delta expected for stable-OK service, got: {match}"

    def test_stable_fail_produces_no_delta(self):
        svc = "d2m-mcp"
        prev_state = {"services": {svc: "failed"}, "last_failure_restart_times": {}}
        curr_scan = self._make_minimal_scan({svc: "failed"})

        deltas = wdog.compare_states(prev_state, curr_scan)
        match = [d for d in deltas if d["service"] == svc]

        assert not match, f"No delta expected for persistent failure, got: {match}"

    def test_multiple_transitions_detected(self):
        """Two services change state simultaneously — both deltas produced."""
        svc_a = "hale-draft-engine"        # Tier 1
        svc_b = "d2m-mcp"                  # Tier 2

        prev_state = {
            "services": {svc_a: "active", svc_b: "failed"},
            "last_failure_restart_times": {},
        }
        curr_scan = self._make_minimal_scan({svc_a: "failed", svc_b: "active"})

        deltas = wdog.compare_states(prev_state, curr_scan)
        services_in_deltas = {d["service"] for d in deltas}

        assert svc_a in services_in_deltas, f"Expected delta for {svc_a}"
        assert svc_b in services_in_deltas, f"Expected delta for {svc_b}"

        a_delta = next(d for d in deltas if d["service"] == svc_a)
        b_delta = next(d for d in deltas if d["service"] == svc_b)
        assert a_delta["direction"] == "degraded"
        assert b_delta["direction"] == "recovered"


# ─── Test 4: Restart recovery — max 3 retries per hour ───────────────────────

class TestRestartRecovery:
    """Verify attempt_recovery respects MAX_RESTARTS_PER_HOUR cap (3)."""

    def _make_restart_times(self, svc: str, n: int, minutes_ago: int = 5) -> dict:
        """Return restart_times dict with n recent entries for svc."""
        base = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        times = [(base + timedelta(seconds=i * 30)).isoformat() for i in range(n)]
        return {svc: times}

    def test_first_restart_allowed(self):
        svc = "hale-draft-engine"
        restart_times: dict = {}

        with patch.object(wdog, "_run") as mock_run:
            mock_run.return_value = (0, "OK")
            success, updated = wdog.attempt_recovery(svc, restart_times)

        assert success is True
        assert svc in updated
        assert len(updated[svc]) == 1

    def test_second_restart_allowed(self):
        svc = "hale-draft-engine"
        restart_times = self._make_restart_times(svc, 1)

        with patch.object(wdog, "_run", return_value=(0, "OK")):
            success, updated = wdog.attempt_recovery(svc, restart_times)

        assert success is True
        assert len(updated[svc]) == 2

    def test_third_restart_allowed(self):
        svc = "hale-draft-engine"
        restart_times = self._make_restart_times(svc, 2)

        with patch.object(wdog, "_run", return_value=(0, "OK")):
            success, updated = wdog.attempt_recovery(svc, restart_times)

        assert success is True
        assert len(updated[svc]) == 3

    def test_fourth_restart_blocked(self):
        """At cap (3 already done this hour), recovery must be skipped."""
        svc = "hale-draft-engine"
        restart_times = self._make_restart_times(svc, wdog.MAX_RESTARTS_PER_HOUR)

        with patch.object(wdog, "_run") as mock_run:
            success, updated = wdog.attempt_recovery(svc, restart_times)

        assert success is False
        # _run should NOT have been called for restart (only reset-failed is ever called)
        restart_calls = [c for c in mock_run.call_args_list
                         if "restart" in str(c)]
        assert not restart_calls, "systemctl restart should NOT be called when cap reached"
        # Count must remain at MAX
        assert len(updated[svc]) == wdog.MAX_RESTARTS_PER_HOUR

    def test_old_restarts_outside_window_do_not_count(self):
        """Restarts >1 hour ago must not count toward the cap."""
        svc = "hale-draft-engine"
        # 4 restarts from 90 minutes ago — outside the 60-min window
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat()
        restart_times = {svc: [old_time] * 4}

        with patch.object(wdog, "_run", return_value=(0, "OK")):
            success, updated = wdog.attempt_recovery(svc, restart_times)

        assert success is True  # Old restarts don't count; this attempt is allowed

    def test_failed_restart_records_attempt(self):
        """Even a failed restart records the attempt (so the cap counts it)."""
        svc = "hale-draft-engine"
        restart_times: dict = {}

        with patch.object(wdog, "_run", return_value=(1, "Failed to restart")):
            success, updated = wdog.attempt_recovery(svc, restart_times)

        assert success is False
        assert len(updated.get(svc, [])) == 1


# ─── Test 5: Deduplication — don't escalate same failure twice in 30min ──────

class TestEscalationDeduplication:
    """Verify escalation engine deduplicates within the configured windows."""

    def _make_failure(self, svc="thunderbird-mcp", tier=2):
        return {
            "service_name": svc,
            "tier": tier,
            "failure_reason": "service failed",
            "diagnostics": "fake diag",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "self_healing_attempted": True,
            "self_healing_result": "restart failed",
        }

    def test_first_mission_board_escalation_fires(self, tmp_path):
        """First call to escalate_to_mission_board must succeed (not deduped)."""
        failure = self._make_failure()

        # Patch board I/O so we don't need a real mission_board.json
        board_data = {"active_missions": [], "suspended_missions": [], "completed_missions": []}

        def fake_acquire_lock():
            return None

        def fake_load_board():
            return board_data

        def fake_save_board(board, fd):
            board_data.update(board)

        def fake_now_iso():
            return datetime.now(timezone.utc).isoformat()

        with patch("thunderbird_coo_escalation.sys.path"):
            with patch.dict("sys.modules", {
                "mission_board_sync": MagicMock(
                    load_board=fake_load_board,
                    save_board=fake_save_board,
                    acquire_lock=fake_acquire_lock,
                    now_iso=fake_now_iso,
                )
            }):
                result = esc.escalate_to_mission_board(failure)

        assert result is True

    def test_second_mission_board_escalation_within_window_is_deduped(self):
        """Second call within 30 min must be rejected by in-process dedup."""
        svc = "d2m-tunnel"
        failure = self._make_failure(svc=svc)

        # Manually set in-process dedup state as if first escalation just happened
        esc._dedup_state[svc] = {"mission": datetime.now(timezone.utc)}

        result = esc.escalate_to_mission_board(failure)

        assert result is False

    def test_escalation_after_dedup_window_fires_again(self):
        """Escalation older than 30 min must be allowed again."""
        svc = "hale-brief-generate"
        failure = self._make_failure(svc=svc)

        # Set in-process dedup to 35 minutes ago — outside window
        esc._dedup_state[svc] = {
            "mission": datetime.now(timezone.utc) - timedelta(minutes=35)
        }

        board_data = {"active_missions": [], "suspended_missions": [], "completed_missions": []}

        with patch.dict("sys.modules", {
            "mission_board_sync": MagicMock(
                load_board=lambda: board_data,
                save_board=lambda b, fd: board_data.update(b),
                acquire_lock=lambda: None,
                now_iso=lambda: datetime.now(timezone.utc).isoformat(),
            )
        }):
            result = esc.escalate_to_mission_board(failure)

        assert result is True

    def test_email_escalation_skipped_for_tier2(self):
        """Email escalation must only fire for Tier 1."""
        failure = self._make_failure(tier=2)
        result = esc.escalate_to_email(failure)
        assert result is False

    def test_email_dedup_within_one_hour(self):
        """Two Tier 1 email escalations within 60 min — second must be deduped."""
        svc = "hale-draft-engine"
        failure = self._make_failure(svc=svc, tier=1)

        # Mark as escalated now
        esc._dedup_state[svc] = {"email": datetime.now(timezone.utc)}

        result = esc.escalate_to_email(failure)
        assert result is False

    def test_log_escalation_writes_to_log_file(self):
        """log_escalation must write a line to the escalation log file."""
        failure = self._make_failure()
        esc.log_escalation(failure, "mission_board", result="CREATED TEST-001")

        assert esc.LOG_FILE.exists()
        log_content = esc.LOG_FILE.read_text()
        assert "thunderbird-mcp" in log_content
        assert "mission_board" in log_content
        assert "CREATED TEST-001" in log_content

    def test_within_dedup_window_exact_boundary(self):
        """Test boundary: exactly at window edge should still be within."""
        svc = "some-service"
        esc._dedup_state[svc] = {
            "mission": datetime.now(timezone.utc) - timedelta(minutes=29, seconds=59)
        }
        assert esc._within_dedup_window(svc, "mission", 30) is True

    def test_outside_dedup_window_boundary(self):
        """Test boundary: just past window edge should be outside."""
        svc = "some-service"
        esc._dedup_state[svc] = {
            "mission": datetime.now(timezone.utc) - timedelta(minutes=30, seconds=1)
        }
        assert esc._within_dedup_window(svc, "mission", 30) is False
