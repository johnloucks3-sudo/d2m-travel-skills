"""
Regression test — SPAWN-PROMPT-CHECK delivery-override voiding.

Sterling audit 2026-07-08: the original delivery-override fix (commit staged
same day) voided the eval/review exemption on paper but 10 of its 12 override
terms don't contain the substring "send to", so the subsequent
`any(term in prompt for term in _SPAWN_SEND_TERMS)` check independently
returned False for them and the gate never fired. The fix's own repro case
in its code comment ("opus review this and send the client the quote") did
not actually trigger a block before this test existed. Run this file any time
_SPAWN_EVAL_EXEMPT_TERMS, _SPAWN_DELIVERY_OVERRIDE_TERMS, or _SPAWN_SEND_TERMS
change.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.policy.rules_registry import (
    _p_spawn_prompt,
    _SPAWN_DELIVERY_OVERRIDE_TERMS,
    _SPAWN_EVAL_EXEMPT_TERMS,
)


def _ctx(payload: str) -> dict:
    return {"tool": "spawn", "action": "spawn", "payload": payload}


def test_pure_eval_exemption_still_holds_with_no_delivery_language():
    assert _p_spawn_prompt(_ctx("opus review this plan for Nancy Lyons")) is False


def test_pure_eval_exemption_holds_with_no_recipient_identifier():
    # Delivery language present but no name/email to assert a client target —
    # rule 13 requires an identifier, unaffected by the override fix.
    assert _p_spawn_prompt(_ctx("opus review this plan and send the client the quote")) is False


def test_every_override_term_trips_gate_when_paired_with_a_name():
    for term in _SPAWN_DELIVERY_OVERRIDE_TERMS:
        prompt = f"opus review this plan and {term} Nancy Lyons"
        assert _p_spawn_prompt(_ctx(prompt)) is True, f"override term did not fire gate: {term!r}"


def test_every_override_term_trips_gate_when_paired_with_an_email():
    for term in _SPAWN_DELIVERY_OVERRIDE_TERMS:
        prompt = f"opus review this plan and {term} nancy@example.com"
        assert _p_spawn_prompt(_ctx(prompt)) is True, f"override term did not fire gate: {term!r}"


def test_original_reported_bypass_repro_now_blocks_with_identifier():
    prompt = "opus review this plan and send the client Nancy Lyons the quote"
    assert _p_spawn_prompt(_ctx(prompt)) is True


def test_eval_exemption_terms_unaffected_by_override_fix():
    for term in _SPAWN_EVAL_EXEMPT_TERMS:
        prompt = f"{term} for the upcoming trip, no delivery involved"
        assert _p_spawn_prompt(_ctx(prompt)) is False, f"exempt term falsely gated: {term!r}"


def test_no_send_intent_at_all_never_gates():
    assert _p_spawn_prompt(_ctx("just review this plan, nothing else")) is False


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
