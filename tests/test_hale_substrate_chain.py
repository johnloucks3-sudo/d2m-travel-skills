"""
Integration tests for hale_substrate_chain (the dispatcher glue).
Verifies all 3 layers fire in the correct precedence.
"""
import sys
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD_ROOT))
sys.path.insert(0, str(THUNDERBIRD_ROOT / "agents"))

import pytest
from agents import hale_substrate_chain as chain
from core.ops.correction_memory import CorrectionMemory
from core.ops.hale_escalation_supervisor import HaleEscalationSupervisor


@pytest.fixture(autouse=True)
def reset_singletons(monkeypatch, tmp_path):
    """Reset module singletons + use tmp store between tests."""
    fresh_store = tmp_path / "correction_memory.json"
    chain._correction_memory = CorrectionMemory(store_path=fresh_store, lock_threshold=2)
    chain._supervisor = HaleEscalationSupervisor(
        spawn_fn=lambda p: "Sonnet replied: did the thing. Verified.",
        escalation_log=tmp_path / "esc.log",
    )
    yield


# ─── Layer 1 only ───────────────────────────────────────────────────────
class TestLayer1:
    def test_hale_persona_routes_to_sonnet(self):
        r = chain.select_substrate("Hale, status please")
        assert r["substrate"] == "sonnet"
        assert r["source"] == "layer1_keyword_router"

    def test_opus_request_routes_to_opus(self):
        r = chain.select_substrate("/opus rewrite charter")
        assert r["substrate"] == "opus"

    def test_routine_returns_default(self):
        r = chain.select_substrate("ls -la", default="haiku")
        assert r["substrate"] == "haiku"
        assert r["source"] == "default"


# ─── Layer 4 overrides Layer 1 default ──────────────────────────────────
class TestLayer4Override:
    def test_locked_topic_overrides_routine(self):
        chain.record_correction("Wrong.", "Validate McLeod dossier", "")
        chain.record_correction("Wrong again.", "Validate McLeod dossier FPD", "")
        r = chain.select_substrate("Validate McLeod dossier")
        assert r["substrate"] == "sonnet"
        assert r["source"] == "layer4_correction_memory"


# ─── Full dispatch with Layer 3 supervision ─────────────────────────────
class TestFullDispatch:
    def test_clean_haiku_passes_through(self):
        def model(substrate, request):
            return "Done. Verified."
        r = chain.dispatch("Routine status", call_model=model)
        assert r["substrate_used"] == "haiku"
        assert r["escalated"] is False

    def test_hedging_haiku_gets_escalated(self):
        def model(substrate, request):
            return "Should I send the email? Let me know if you want me to."
        r = chain.dispatch("Routine status", call_model=model)
        assert r["escalated"] is True
        assert r["substrate_used"] == "sonnet"
        assert "Sonnet replied" in r["response"]

    def test_hale_request_skips_supervisor(self):
        def model(substrate, request):
            return "Should I send the email? Let me know if you want me to."
        r = chain.dispatch("Hale brief please", call_model=model)
        # Hale-tier already routed to Sonnet — supervisor skipped, no escalation.
        assert r["substrate_used"] == "sonnet"
        assert r["escalated"] is False
        assert r["supervision"] is None

    def test_supervisor_disabled(self):
        def model(substrate, request):
            return "Should I send the email?"
        r = chain.dispatch(
            "Routine", call_model=model, enable_supervisor=False
        )
        assert r["escalated"] is False


# ─── End-to-end: precedence chain ───────────────────────────────────────
class TestPrecedence:
    def test_layer4_beats_layer1_routine(self):
        # Lock a topic
        chain.record_correction("Wrong.", "send Westbrook itinerary", "")
        chain.record_correction("Wrong again.", "send Westbrook itinerary today", "")
        # Even though "send Westbrook" doesn't match Layer 1 Hale pattern,
        # the lock forces sonnet.
        r = chain.select_substrate("Send Westbrook itinerary")
        assert r["substrate"] == "sonnet"
        assert r["source"] == "layer4_correction_memory"

    def test_layer1_opus_when_topic_below_similarity(self):
        # Lock a focused McLeod-validation topic
        chain.record_correction("Wrong.", "Validate McLeod dossier", "")
        chain.record_correction("Wrong.", "Validate McLeod dossier FPD", "")
        # Request differs enough that similarity is below threshold —
        # so Layer 4 does NOT fire, and Layer 1 Opus wins.
        r = chain.select_substrate("/opus arbitrate the broader strategic conflict")
        assert r["substrate"] == "opus"
        assert r["source"] == "layer1_keyword_router"

    def test_layer4_sonnet_overrides_layer1_when_topic_matches(self):
        chain.record_correction("Wrong.", "Validate McLeod dossier", "")
        chain.record_correction("Wrong.", "Validate McLeod dossier FPD", "")
        # Request matches locked topic AND would Layer-1 to Sonnet anyway.
        # Layer 4 fires first and reports its source.
        r = chain.select_substrate("Validate McLeod dossier please")
        assert r["substrate"] == "sonnet"
        assert r["source"] == "layer4_correction_memory"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
