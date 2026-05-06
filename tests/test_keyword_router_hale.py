"""
Tests for keyword_router.classify_substrate (Layer 1 of Hale Escalation).
Validates substrate routing for OPUS / HALE / ROUTINE patterns.
"""
import sys
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD_ROOT / "OpsCenter"))

import pytest
from keyword_router import classify_substrate


# ─── OPUS-TIER (highest precedence) ─────────────────────────────────────
class TestOpusTier:
    def test_long_term_strategy(self):
        d = classify_substrate("What's our long-term growth strategy?")
        assert d["substrate"] == "opus"
        assert d["tier"] == "OPUS-TIER"

    def test_arbitrate_keyword(self):
        d = classify_substrate("Models disagree — please arbitrate.")
        assert d["substrate"] == "opus"

    def test_explicit_opus_request(self):
        d = classify_substrate("/opus rewrite the SO")
        assert d["substrate"] == "opus"

    def test_first_principles(self):
        d = classify_substrate("Reset from first principles. New charter.")
        assert d["substrate"] == "opus"

    def test_use_opus(self):
        d = classify_substrate("Use Opus please for this synthesis")
        assert d["substrate"] == "opus"


# ─── HALE-TIER (Sonnet) ─────────────────────────────────────────────────
class TestHaleTier:
    def test_persona_invocation_hale(self):
        d = classify_substrate("Hale, status please")
        assert d["substrate"] == "sonnet"
        assert d["tier"] == "HALE-TIER"

    def test_chief_of_staff(self):
        d = classify_substrate("Chief of Staff brief")
        assert d["substrate"] == "sonnet"

    def test_iron_vic(self):
        d = classify_substrate("Iron Vic, what do you recommend?")
        assert d["substrate"] == "sonnet"

    def test_strategic_verb_decide(self):
        d = classify_substrate("Decide whether to push the McLeod proposal today")
        assert d["substrate"] == "sonnet"

    def test_strategic_verb_synthesize(self):
        d = classify_substrate("Synthesize the three intel sweeps into a brief")
        assert d["substrate"] == "sonnet"

    def test_root_cause(self):
        d = classify_substrate("Root cause analysis on the Telegram bot conflict")
        assert d["substrate"] == "sonnet"

    def test_compare_tradeoffs(self):
        d = classify_substrate("Compare Silversea and Regent — what's the tradeoff?")
        assert d["substrate"] == "sonnet"

    def test_should_we(self):
        d = classify_substrate("Should we send Westbrook the itinerary today?")
        assert d["substrate"] == "sonnet"

    def test_options_framework(self):
        d = classify_substrate("What are our options here?")
        assert d["substrate"] == "sonnet"

    def test_mission_board_p1(self):
        d = classify_substrate("Mission board P1 status?")
        assert d["substrate"] == "sonnet"

    def test_lifecycle_fpd(self):
        d = classify_substrate("Kuklinski FPD validation — where are we?")
        assert d["substrate"] == "sonnet"

    def test_vocative_sir(self):
        d = classify_substrate("Sir, what's the priority for this morning?")
        assert d["substrate"] == "sonnet"

    def test_vocative_yoda(self):
        d = classify_substrate("Yoda, brief on the wing")
        assert d["substrate"] == "sonnet"

    def test_vocative_commander(self):
        d = classify_substrate("Commander, here's the situation")
        assert d["substrate"] == "sonnet"

    def test_root_cause_question(self):
        d = classify_substrate("Why is the Haiku supervisor not catching this?")
        assert d["substrate"] == "sonnet"

    def test_multi_step_framing(self):
        d = classify_substrate("First scan the inbox, then triage, finally summarize")
        assert d["substrate"] == "sonnet"


# ─── ROUTINE (Haiku stays) ──────────────────────────────────────────────
class TestRoutine:
    def test_simple_status(self):
        d = classify_substrate("What time is it in Athens?")
        assert d["substrate"] == "haiku"
        assert d["tier"] == "ROUTINE"

    def test_is_running(self):
        d = classify_substrate("Is nexus.service running?")
        assert d["substrate"] == "haiku"

    def test_read_file(self):
        d = classify_substrate("Read file /tmp/foo.txt")
        assert d["substrate"] == "haiku"

    def test_format_as_json(self):
        d = classify_substrate("Format this as JSON for me")
        assert d["substrate"] == "haiku"

    def test_no_pattern(self):
        d = classify_substrate("foo bar baz")
        assert d["substrate"] == "haiku"
        assert d["tier"] == "ROUTINE"

    def test_empty(self):
        d = classify_substrate("")
        assert d["substrate"] == "haiku"
        assert d["tier"] == "ROUTINE"


# ─── Precedence: Opus > Sonnet > Haiku ──────────────────────────────────
class TestPrecedence:
    def test_opus_beats_hale(self):
        d = classify_substrate("Hale, please use Opus to compare these")
        assert d["substrate"] == "opus", "explicit Opus invocation must win over Hale persona"

    def test_hale_beats_routine(self):
        # Hale-tier "options" should win over routine even if request is short
        d = classify_substrate("Read file but also synthesize the options")
        assert d["substrate"] == "sonnet"

    def test_decision_matched_patterns_present(self):
        d = classify_substrate("Hale should we compare these tradeoffs")
        assert d["substrate"] == "sonnet"
        assert len(d["matched_patterns"]) >= 2


# ─── Reason field present and informative ───────────────────────────────
class TestReasoning:
    def test_reason_for_opus(self):
        d = classify_substrate("/opus")
        assert "OPUS-TIER" in d["reason"]

    def test_reason_for_hale(self):
        d = classify_substrate("Hale")
        assert "HALE-TIER" in d["reason"]

    def test_reason_for_routine(self):
        d = classify_substrate("ls -la")
        assert "ROUTINE" in d["reason"] or "routine" in d["reason"].lower() or "no" in d["reason"].lower()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
