"""
Tests for HaleEscalationSupervisor (Layer 3 of Hale Escalation).
Validates escalation triggers and the silent re-run path.
All model calls are mocked — no real subprocess invocations.
"""
import sys
import json
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD_ROOT))

import pytest
from core.ops.hale_escalation_supervisor import (
    HaleEscalationSupervisor,
    _matches_banned,
    _hedge_density_violations,
    _options_menu_count,
    _is_decision_deferral,
    _is_underweight_multistep,
)


# ─── Trigger detection: banned phrases ──────────────────────────────────
class TestBannedPhrases:
    def test_should_i_send(self):
        assert _matches_banned("Should I send the email now?")

    def test_would_you_like(self):
        assert _matches_banned("Would you like me to proceed?")

    def test_shall_i(self):
        assert _matches_banned("Shall I draft the response?")

    def test_awaiting_confirmation(self):
        assert _matches_banned("Awaiting your confirmation before proceeding.")

    def test_ready_to_execute(self):
        assert _matches_banned("Ready to execute when you give the word.")

    def test_let_me_know(self):
        assert _matches_banned("Let me know if you want me to send it.")

    def test_standing_by_no_gate(self):
        assert "standing by (no gate context)" in _matches_banned("Standing by.")

    def test_standing_by_at_gate_allowed(self):
        # Gate-relevant standing by is OK.
        result = _matches_banned("Standing by at WF-17 gate for client send approval.")
        assert "standing by (no gate context)" not in result

    def test_clean_response(self):
        assert _matches_banned("Done. Sent. Logged the decision.") == []


# ─── Trigger detection: hedge density ───────────────────────────────────
class TestHedgeDensity:
    def test_high_hedge_paragraph(self):
        text = "I think maybe we could perhaps possibly try this approach."
        assert _hedge_density_violations(text) >= 1

    def test_low_hedge_ok(self):
        text = "Maybe we should try this. Then verify the result."
        assert _hedge_density_violations(text) == 0

    def test_clean_response(self):
        text = "Done. Sent the validation email. McLeod replied."
        assert _hedge_density_violations(text) == 0


# ─── Trigger detection: options menu ────────────────────────────────────
class TestOptionsMenu:
    def test_three_options_format(self):
        text = "Option 1: Send it. Option 2: Hold it. Option 3: Revise it."
        assert _options_menu_count(text) >= 3

    def test_two_options_below_threshold(self):
        text = "Option 1: Send it. Option 2: Hold it."
        assert _options_menu_count(text) < 3

    def test_no_options(self):
        assert _options_menu_count("Sent the email. Updated dossier.") == 0


# ─── Trigger detection: decision deferral ───────────────────────────────
class TestDecisionDeferral:
    def test_your_call(self):
        assert _is_decision_deferral("All set. Your call.", "Run the audit")

    def test_let_me_know_which(self):
        assert _is_decision_deferral(
            "Drafted A and B. Let me know which you prefer.",
            "Draft a follow-up to McLeod"
        )

    def test_gate_context_exempt(self):
        # If the original request is gate-relevant, deferral is fine.
        assert not _is_decision_deferral(
            "Draft ready. Your call.",
            "WF-17: review draft before client send"
        )

    def test_no_deferral(self):
        assert not _is_decision_deferral("Done. Sent it.", "Send the email")


# ─── Trigger detection: underweight multi-step ──────────────────────────
class TestUnderweightMultistep:
    def test_multistep_short_response_triggers(self):
        request = "First scan inbox, then triage P1, finally summarize for the brief"
        response = "OK done."
        assert _is_underweight_multistep(response, request)

    def test_multistep_long_response_passes(self):
        request = "First scan inbox, then triage P1, finally summarize for the brief"
        response = " ".join(["word"] * 80)
        assert not _is_underweight_multistep(response, request)

    def test_single_step_request_skipped(self):
        request = "Send the email"
        response = "OK"
        assert not _is_underweight_multistep(response, request)


# ─── inspect_response composite behavior ────────────────────────────────
class TestInspectResponse:
    def setup_method(self):
        self.sup = HaleEscalationSupervisor(spawn_fn=lambda p: "[mocked sonnet output]")

    def test_clean_haiku_response_passes(self):
        d = self.sup.inspect_response(
            request="Status update", response="Done. Sent.",
            current_substrate="haiku",
        )
        assert d["escalate"] is False

    def test_should_i_triggers_escalation(self):
        d = self.sup.inspect_response(
            request="Send the email",
            response="Should I send the email now?",
            current_substrate="haiku",
        )
        assert d["escalate"] is True
        assert any("banned_phrases" in t for t in d["matched_triggers"])

    def test_options_menu_triggers(self):
        d = self.sup.inspect_response(
            request="What should we do",
            response="Option 1: A. Option 2: B. Option 3: C.",
            current_substrate="gemini-flash",
        )
        assert d["escalate"] is True

    def test_skipped_when_already_sonnet(self):
        d = self.sup.inspect_response(
            request="Should I do X",
            response="Should I send the email?",
            current_substrate="sonnet",
        )
        assert d["escalate"] is False
        assert "already Sonnet-tier" in d["reason"]

    def test_skipped_when_opus(self):
        d = self.sup.inspect_response(
            request="x", response="Should I send it?",
            current_substrate="opus",
        )
        assert d["escalate"] is False

    def test_empty_response_no_escalation(self):
        d = self.sup.inspect_response(
            request="x", response="",
            current_substrate="haiku",
        )
        assert d["escalate"] is False

    def test_underweight_multistep_triggers(self):
        d = self.sup.inspect_response(
            request="First do A, then do B, finally do C across all clients",
            response="Yes.",
            current_substrate="haiku",
        )
        assert d["escalate"] is True


# ─── escalate() invokes spawn_fn and logs ───────────────────────────────
class TestEscalate:
    def test_escalate_returns_new_response(self, tmp_path):
        log_path = tmp_path / "esc.log"
        sup = HaleEscalationSupervisor(
            spawn_fn=lambda p: "Hale-tier reply: did X. Verification: Y.",
            escalation_log=log_path,
        )
        out = sup.escalate("Send email", "Should I send?")
        assert "Hale-tier reply" in out

        # Verify escalation event was logged
        contents = log_path.read_text()
        events = [json.loads(line) for line in contents.strip().split("\n") if line]
        assert any(e["event"] == "escalation_succeeded" for e in events)

    def test_escalate_failure_returns_original(self, tmp_path):
        log_path = tmp_path / "esc.log"

        def boom(_p):
            raise RuntimeError("simulated failure")

        sup = HaleEscalationSupervisor(spawn_fn=boom, escalation_log=log_path)
        original = "Should I send?"
        out = sup.escalate("Send email", original)
        # Falls back to original
        assert out == original
        contents = log_path.read_text()
        events = [json.loads(line) for line in contents.strip().split("\n") if line]
        assert any(e["event"] == "escalation_failed" for e in events)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
