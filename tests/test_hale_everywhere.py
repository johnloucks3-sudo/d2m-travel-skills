"""
test_hale_everywhere.py — End-to-end integration tests for Hale dispatch wire-up.

Covers all five sub-builds:
  A. Telegram Hale Router (OpsCenter/telegram_hale_router.py)
  B. OpenCode Hale Shim (agents/opencode_hale_shim.py)
  C. Email Hale Dispatch (agents/email_hale_dispatch.py)
  D. Morning Brief Telemetry (agents/morning_brief_telemetry.py)
  E. End-to-end smoke (real dispatch_with_telemetry, simulated model, real telemetry write)

No real model calls are made. All external model + subprocess dependencies are mocked.
"""

from __future__ import annotations

import json
import sys
import threading
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD_ROOT))
sys.path.insert(0, str(THUNDERBIRD_ROOT / "OpsCenter"))

# ── Module imports (must come after sys.path setup) ───────────────────────────
import telegram_hale_router as thr
from agents.opencode_hale_shim import should_use_hale as oc_should_use_hale
from agents.opencode_hale_shim import dispatch_through_hale
from agents.email_hale_dispatch import handle_email_task, is_hale_tier_email
from agents.morning_brief_telemetry import telemetry_section, telemetry_section_html
from agents.hale_dispatcher_runtime import dispatch_with_telemetry
import core.ops.dispatch_telemetry as _telemetry_mod
from core.ops.dispatch_telemetry import daily_rollup
from core.ops.correction_memory import CorrectionMemory


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_thr_last_turn():
    """Reset telegram_hale_router's per-chat last-turn tracker between tests."""
    with thr._turn_lock:
        thr._last_turn.clear()
    yield
    with thr._turn_lock:
        thr._last_turn.clear()


@pytest.fixture()
def fake_sonnet_selection():
    """Mock select_substrate to return Hale-tier (sonnet)."""
    return {
        "substrate": "sonnet",
        "source": "layer1_keyword_router",
        "reason": "matched HALE-TIER pattern: hale",
        "classification": {"substrate": "sonnet", "tier": "HALE-TIER"},
    }


@pytest.fixture()
def fake_haiku_selection():
    """Mock select_substrate to return routine (haiku)."""
    return {
        "substrate": "haiku",
        "source": "default",
        "reason": "no Hale/Opus pattern detected — routine default",
        "classification": {"substrate": "haiku", "tier": "ROUTINE"},
    }


@pytest.fixture()
def fake_dispatch_result():
    """Canned dispatch_with_telemetry return value."""
    return {
        "response": "Done. Dossier updated. Sending sweep at 06:00.",
        "substrate_used": "sonnet",
        "escalated": False,
        "selection": {
            "substrate": "sonnet",
            "source": "layer1_keyword_router",
            "reason": "matched HALE-TIER pattern: hale",
            "classification": None,
        },
        "supervision": None,
        "duration_s": 1.2,
        "telemetry": {
            "ts": "2026-05-04T06:00:00+00:00",
            "substrate": "sonnet",
            "executed_via": "max_oauth",
            "escalated": False,
            "cost_actual_usd": 0.0,
            "cost_would_be_api_usd": 0.0012,
            "savings_usd": 0.0012,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUB-BUILD A — Telegram Hale Router
# ─────────────────────────────────────────────────────────────────────────────

class TestTelegramHaleRouter:
    """Test A1/A2/A3: commands, correction detection, routing."""

    # ── A1 / A3: Hale-tier message → should route through dispatcher ──────────

    def test_hale_tier_message_detected(self, fake_sonnet_selection):
        """Hale-tier text correctly detected as needing dispatcher routing."""
        with patch.object(thr, "select_substrate", return_value=fake_sonnet_selection):
            result = thr.should_use_hale("Hale, what's the McLeod FPD status?")
        assert result is True

    def test_hale_tier_get_response_calls_dispatcher(self, fake_dispatch_result):
        """get_hale_response delegates to dispatch_with_telemetry and returns the string."""
        with patch.object(thr, "dispatch_with_telemetry", return_value=fake_dispatch_result):
            response = thr.get_hale_response("Hale, status please", channel="telegram")
        assert response == fake_dispatch_result["response"]

    # ── A3: Routine message → should NOT route through dispatcher ────────────

    def test_routine_message_not_routed(self, fake_haiku_selection):
        """Routine messages return False — existing engine path kept."""
        with patch.object(thr, "select_substrate", return_value=fake_haiku_selection):
            result = thr.should_use_hale("what time is it in Athens?")
        assert result is False

    # ── A1: /dispatch_status command ─────────────────────────────────────────

    def test_dispatch_status_text_returns_string(self):
        """/dispatch_status returns a non-empty string."""
        fake_report = "📊 DISPATCH TELEMETRY — 2026-05-04\nTotal dispatches: 5"
        with patch.object(thr, "status_report", return_value=fake_report):
            text = thr.dispatch_status_text()
        assert text == fake_report

    # ── A1: /savings command ──────────────────────────────────────────────────

    def test_savings_text_with_activity(self):
        """/savings returns formatted savings string when activity exists."""
        fake_rollup = {
            "total_dispatches": 10,
            "savings_total_usd": 0.0456,
            "max_oauth_pct": 90.0,
        }
        with patch.object(thr, "daily_rollup", return_value=fake_rollup):
            text = thr.savings_text()
        assert "$0.0456" in text
        assert "90%" in text

    def test_savings_text_no_activity(self):
        """/savings returns sentinel string when no dispatches today."""
        with patch.object(thr, "daily_rollup", return_value={"total_dispatches": 0}):
            text = thr.savings_text()
        assert "No dispatch activity" in text

    # ── A2: Correction detection ───────────────────────────────────────────────

    def test_correction_detected_and_logged(self):
        """Commander sends correction after bot response → record_correction called."""
        chat_id = 7554895206
        prior_request = "Should we send the McLeod proposal today?"
        prior_response = "Should I send the email? Let me know if you want me to."

        # Set up the prior turn
        thr.record_turn(chat_id, prior_request, prior_response)

        # Commander sends a correction
        with patch.object(thr, "record_correction") as mock_record:
            thr.check_correction(chat_id, "No, that's wrong. Just do it.")

        mock_record.assert_called_once_with(
            commander_message="No, that's wrong. Just do it.",
            prior_request=prior_request,
            prior_response=prior_response,
        )

    def test_non_correction_not_logged(self):
        """Normal follow-up message does not trigger correction logging."""
        chat_id = 7554895206
        thr.record_turn(chat_id, "Show status", "Wing is GREEN.")

        with patch.object(thr, "record_correction") as mock_record:
            thr.check_correction(chat_id, "Great, thanks for the update")

        mock_record.assert_not_called()

    def test_correction_without_prior_turn_is_noop(self):
        """Correction pattern on a chat with no tracked turn → no crash, no call."""
        chat_id = 9999  # Never had a turn recorded
        with patch.object(thr, "record_correction") as mock_record:
            thr.check_correction(chat_id, "No, that's wrong")
        mock_record.assert_not_called()

    def test_correction_for_routine_engine_response(self):
        """record_turn for a routine-engine response; correction on next message logs it."""
        chat_id = 7554895206
        routine_request = "What is today's date?"
        routine_response = "Should I check that for you?"  # hedging haiku response

        thr.record_turn(chat_id, routine_request, routine_response)

        with patch.object(thr, "record_correction") as mock_record:
            thr.check_correction(chat_id, "No, that's wrong. Just tell me.")

        mock_record.assert_called_once_with(
            commander_message="No, that's wrong. Just tell me.",
            prior_request=routine_request,
            prior_response=routine_response,
        )

    def test_record_turn_thread_safety(self):
        """Multiple threads can write record_turn without race."""
        errors = []

        def write_turn(i: int):
            try:
                thr.record_turn(i, f"request_{i}", f"response_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_turn, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        with thr._turn_lock:
            assert len(thr._last_turn) == 50


# ─────────────────────────────────────────────────────────────────────────────
# SUB-BUILD B — OpenCode Hale Shim
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenCodeHaleShim:
    """Test B: should_use_hale and dispatch_through_hale."""

    def test_hale_query_detected(self):
        """FPD question with 'Hale' keyword → True."""
        result = oc_should_use_hale("Hale, what's the FPD for the McLeod booking?")
        assert result is True

    def test_routine_query_not_hale(self):
        """Simple lookup → False."""
        result = oc_should_use_hale("ls -la /home/john/Thunderbird/output/")
        assert result is False

    def test_strategy_query_is_hale_tier(self):
        """Strategy keyword → True (Sonnet tier)."""
        result = oc_should_use_hale("What strategy should we use for the Westbrook upsell?")
        assert result is True

    def test_dispatch_through_hale_returns_string(self, fake_dispatch_result):
        """dispatch_through_hale returns the response string, not the full dict."""
        from agents import opencode_hale_shim as shim
        with patch.object(shim, "dispatch_with_telemetry", return_value=fake_dispatch_result):
            response = dispatch_through_hale(
                "Hale, draft the McLeod follow-up email",
                channel="opencode",
            )
        assert isinstance(response, str)
        assert response == fake_dispatch_result["response"]

    def test_dispatch_through_hale_passes_channel(self, fake_dispatch_result):
        """dispatch_through_hale passes the default_substrate to dispatch_with_telemetry."""
        from agents import opencode_hale_shim as shim
        with patch.object(shim, "dispatch_with_telemetry", return_value=fake_dispatch_result) as mock_disp:
            dispatch_through_hale("Hale, what's the McLeod status?", default_substrate="haiku")
        mock_disp.assert_called_once()
        _, kwargs = mock_disp.call_args
        assert kwargs.get("default_substrate") == "haiku"


# ─────────────────────────────────────────────────────────────────────────────
# SUB-BUILD C — Email Hale Dispatch
# ─────────────────────────────────────────────────────────────────────────────

class TestEmailHaleDispatch:
    """Test C: handle_email_task and is_hale_tier_email."""

    def test_hale_tier_email_detected(self):
        """Subject with strategy keyword is classified as Hale-tier."""
        result = is_hale_tier_email(
            subject="[COS] Strategy review for Q3 bookings",
            body="Please write a strategy brief for the Q3 upsell campaign.",
        )
        assert result is True

    def test_routine_email_not_hale_tier(self):
        """Plain status check not classified as Hale-tier."""
        result = is_hale_tier_email(
            subject="status check",
            body="what is the current status of the Westbrook booking?",
        )
        assert result is False

    def test_handle_email_task_routes_through_dispatcher(self, fake_dispatch_result):
        """handle_email_task calls dispatch_with_telemetry and structures the response."""
        from agents import email_hale_dispatch as ehd
        with patch.object(ehd, "dispatch_with_telemetry", return_value=fake_dispatch_result):
            result = handle_email_task(
                subject="[WING-TASK] Draft Westbrook strategy email",
                body="Commander requests a strategy brief on Westbrook upsell.",
                sender="johnloucks3@gmail.com",
            )

        assert "response" in result
        assert "substrate_used" in result
        assert "telemetry" in result
        assert "selection" in result
        assert result["response"] == fake_dispatch_result["response"]
        assert result["substrate_used"] == fake_dispatch_result["substrate_used"]

    def test_handle_email_task_combines_subject_and_body(self, fake_dispatch_result):
        """The request passed to dispatcher includes both subject and body."""
        from agents import email_hale_dispatch as ehd
        captured = {}

        def capture_dispatch(request, **kwargs):
            captured["request"] = request
            return fake_dispatch_result

        with patch.object(ehd, "dispatch_with_telemetry", side_effect=capture_dispatch):
            handle_email_task(
                subject="[COS] McLeod FPD check",
                body="Please confirm the FPD for McLeod Grandeur booking.",
                sender="johnloucks3@gmail.com",
            )

        assert "McLeod FPD check" in captured["request"]
        assert "confirm the FPD" in captured["request"]
        assert "johnloucks3@gmail.com" in captured["request"]


# ─────────────────────────────────────────────────────────────────────────────
# SUB-BUILD D — Morning Brief Telemetry
# ─────────────────────────────────────────────────────────────────────────────

class TestMorningBriefTelemetry:
    """Test D: telemetry_section and telemetry_section_html."""

    SAMPLE_ROLLUP = {
        "date": "2026-05-03",
        "total_dispatches": 42,
        "max_oauth_pct": 88.0,
        "escalations": 3,
        "savings_total_usd": 0.1234,
        "by_substrate": {"sonnet": 35, "haiku": 7},
        "by_source": {"layer1_keyword_router": 30, "default": 12},
        "by_executed_via": {"max_oauth": 37, "test": 5},
        "tokens_in_total_est": 12000,
        "tokens_out_total_est": 4000,
        "cost_actual_usd_total": 0.0,
        "cost_would_be_api_total": 0.1234,
        "avg_duration_s": 2.1,
    }

    def test_telemetry_section_contains_key_fields(self):
        """telemetry_section returns string with dispatch count, MAX%, escalations, savings."""
        from agents import morning_brief_telemetry as mbt
        yesterday = date.today() - timedelta(days=1)
        with patch.object(mbt, "daily_rollup", return_value=self.SAMPLE_ROLLUP):
            text = telemetry_section(target_date=yesterday)

        assert "42" in text           # total dispatches
        assert "88%" in text          # MAX OAuth pct
        assert "3" in text            # escalations
        assert "$0.1234" in text      # savings
        assert "YESTERDAY'S DISPATCH" in text

    def test_telemetry_section_no_activity_sentinel(self):
        """No-activity day returns sentinel string, not an error."""
        from agents import morning_brief_telemetry as mbt
        empty_rollup = {"total_dispatches": 0, "date": "2026-05-03"}
        with patch.object(mbt, "daily_rollup", return_value=empty_rollup):
            text = telemetry_section()

        assert "no activity" in text.lower()

    def test_telemetry_section_html_contains_html(self):
        """telemetry_section_html returns a <div> block with inline styles."""
        from agents import morning_brief_telemetry as mbt
        with patch.object(mbt, "daily_rollup", return_value=self.SAMPLE_ROLLUP):
            html = telemetry_section_html()

        assert "<div" in html
        assert "42" in html
        assert "$0.1234" in html
        assert "color:#0000ff" in html  # D2M blue

    def test_telemetry_section_html_no_activity_div(self):
        """Even with no activity, telemetry_section_html returns a <div>."""
        from agents import morning_brief_telemetry as mbt
        empty_rollup = {"total_dispatches": 0, "date": "2026-05-03"}
        with patch.object(mbt, "daily_rollup", return_value=empty_rollup):
            html = telemetry_section_html()

        assert "<div" in html
        assert "</div>" in html


# ─────────────────────────────────────────────────────────────────────────────
# SUB-BUILD E — End-to-End Smoke Test
# ─────────────────────────────────────────────────────────────────────────────

class TestE2ESmoke:
    """Test E: real dispatch_with_telemetry → telemetry written → rollup includes it."""

    def test_e2e_dispatch_writes_telemetry(self, tmp_path, monkeypatch):
        """Hale-tier dispatch: telemetry record written, rollup includes the event."""
        # Redirect telemetry I/O to tmp_path so real logs stay clean
        monkeypatch.setattr(_telemetry_mod, "_LOG_PATH", tmp_path / "telemetry.jsonl")
        monkeypatch.setattr(_telemetry_mod, "_ROLLUP_PATH", tmp_path / "rollup.json")

        # Use a tmp correction memory store (avoids file-not-found on fresh install)
        import core.ops.correction_memory as cm_mod
        import agents.hale_substrate_chain as chain
        from core.ops.hale_escalation_supervisor import HaleEscalationSupervisor

        fresh_store = tmp_path / "correction_memory.json"
        chain._correction_memory = CorrectionMemory(store_path=fresh_store, lock_threshold=2)
        chain._supervisor = HaleEscalationSupervisor(
            spawn_fn=lambda p: "Sonnet replied.",
            escalation_log=tmp_path / "esc.log",
        )

        # Dispatch a Hale-tier request without a real model call
        result = dispatch_with_telemetry(
            "Hale, draft the McLeod strategy brief",
            default_substrate="haiku",
            skip_actual_call=True,
            enable_supervisor=False,
        )

        # Substrate should be sonnet (HALE keyword fires)
        assert result["substrate_used"] in ("sonnet", "opus")
        assert result["escalated"] is False

        # Telemetry file should exist with one line
        log_path = tmp_path / "telemetry.jsonl"
        assert log_path.exists(), "telemetry.jsonl was not written"
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1, f"Expected 1 telemetry record, got {len(lines)}"

        record = json.loads(lines[0])
        assert record["substrate"] in ("sonnet", "opus")
        assert record["selection_source"] == "layer1_keyword_router"
        assert "savings_usd" in record

        # daily_rollup should aggregate and include the event
        rollup = daily_rollup()
        assert rollup["total_dispatches"] == 1
        assert rollup["savings_total_usd"] >= 0.0

    def test_e2e_routine_does_not_escalate(self, tmp_path, monkeypatch):
        """Routine request stays on haiku/default and is NOT escalated by supervisor."""
        monkeypatch.setattr(_telemetry_mod, "_LOG_PATH", tmp_path / "telemetry2.jsonl")
        monkeypatch.setattr(_telemetry_mod, "_ROLLUP_PATH", tmp_path / "rollup2.json")

        import agents.hale_substrate_chain as chain
        from core.ops.hale_escalation_supervisor import HaleEscalationSupervisor

        fresh_store = tmp_path / "correction2.json"
        chain._correction_memory = CorrectionMemory(store_path=fresh_store, lock_threshold=2)
        chain._supervisor = HaleEscalationSupervisor(
            spawn_fn=lambda p: "Sonnet escalated.",
            escalation_log=tmp_path / "esc2.log",
        )

        result = dispatch_with_telemetry(
            "list tasks",       # ROUTINE — no Hale keywords
            default_substrate="haiku",
            skip_actual_call=True,
            enable_supervisor=False,
        )

        assert result["substrate_used"] == "haiku"
        assert result["escalated"] is False
        assert result["selection"]["source"] == "default"


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest as _pytest
    sys.exit(_pytest.main([__file__, "-v"]))
