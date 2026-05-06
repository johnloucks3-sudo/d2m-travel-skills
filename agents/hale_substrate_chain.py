#!/usr/bin/env python3
"""
hale_substrate_chain.py — Integration glue for the 3-layer Hale Escalation System
==================================================================================
This module is the integration point for thunderbird_model_dispatcher.py
(and any other call site that wants pre-flight + post-flight Hale routing).

Chain order:
  Layer 4 (CorrectionMemory)           — locked topic? force Sonnet.
  Layer 1 (keyword_router.classify_substrate) — pattern match? upgrade substrate.
  ── execute on chosen substrate ──
  Layer 3 (HaleEscalationSupervisor)   — small substrate output flawed? re-run on Sonnet.

Designed to be ADDITIVE — does not modify the existing dispatch_task path.
Call select_substrate() before model invocation; call run_with_supervisor()
to wrap the full dispatch + supervision cycle.

Author: Thunderbird Wing | 2026-05-04 | SO_HALE_REAL_AUTONOMY_20260504
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional

# Path-insert (matches existing project import convention)
_ROOT = Path("/home/john/Thunderbird")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "OpsCenter") not in sys.path:
    sys.path.insert(0, str(_ROOT / "OpsCenter"))

from keyword_router import classify_substrate                       # Layer 1
from core.ops.correction_memory import CorrectionMemory             # Layer 4
from core.ops.hale_escalation_supervisor import (                   # Layer 3
    HaleEscalationSupervisor,
)


# ─── Module-level singletons (lazy) ──────────────────────────────────────
_correction_memory: Optional[CorrectionMemory] = None
_supervisor: Optional[HaleEscalationSupervisor] = None


def get_correction_memory() -> CorrectionMemory:
    global _correction_memory
    if _correction_memory is None:
        _correction_memory = CorrectionMemory()
    return _correction_memory


def get_supervisor(spawn_fn=None) -> HaleEscalationSupervisor:
    global _supervisor
    if _supervisor is None or spawn_fn is not None:
        _supervisor = HaleEscalationSupervisor(spawn_fn=spawn_fn)
    return _supervisor


# ─── Layer chain ────────────────────────────────────────────────────────
def select_substrate(request: str, default: str = "haiku") -> dict:
    """Run the substrate-selection chain (Layer 4 → Layer 1 → default).

    Args:
        request: Raw request text.
        default: Fallback substrate when no override fires (e.g. "haiku" or "gemini-flash").

    Returns:
        Dict with keys: substrate, source, reason, classification (Layer 1 raw output).
    """
    # Layer 4: locked topics override everything.
    cm = get_correction_memory()
    if cm.should_autoroute_sonnet(request):
        lock = cm.get_lock_reason(request) or {}
        return {
            "substrate": "sonnet",
            "source": "layer4_correction_memory",
            "reason": (
                f"locked topic '{lock.get('topic_summary', '?')}' "
                f"(corrections={lock.get('correction_count', '?')})"
            ),
            "classification": None,
            "lock_info": lock,
        }

    # Layer 1: pattern-based classifier.
    classification = classify_substrate(request)
    if classification["substrate"] in ("sonnet", "opus"):
        return {
            "substrate": classification["substrate"],
            "source": "layer1_keyword_router",
            "reason": classification["reason"],
            "classification": classification,
        }

    # Routine — caller's default substrate.
    return {
        "substrate": default,
        "source": "default",
        "reason": classification["reason"],
        "classification": classification,
    }


def dispatch(
    request: str,
    call_model: Callable[[str, str], str],
    default_substrate: str = "haiku",
    enable_supervisor: bool = True,
) -> dict:
    """Full dispatch cycle: select substrate, call model, supervise output.

    Args:
        request: Raw request text.
        call_model: Function (substrate, request) -> response_text.
                    Caller wires this to whatever model client they use.
        default_substrate: What to use when no Hale-tier override fires.
        enable_supervisor: If False, skip Layer 3 entirely (e.g. for tests).

    Returns:
        Dict with: response, substrate_used, escalated, selection (Layer 1/4 result),
        supervision (Layer 3 result if applicable).
    """
    selection = select_substrate(request, default=default_substrate)
    chosen = selection["substrate"]

    response = call_model(chosen, request)

    supervision = None
    escalated = False
    if enable_supervisor and chosen.lower() in {"haiku", "gemini-flash", "gemini_flash", "flash"}:
        sup = get_supervisor()
        decision = sup.inspect_response(request, response, chosen)
        sup.log_inspection(request, response, chosen, decision)
        supervision = decision
        if decision["escalate"]:
            response = sup.escalate(request, response)
            escalated = True

    return {
        "response": response,
        "substrate_used": "sonnet" if escalated else chosen,
        "escalated": escalated,
        "selection": selection,
        "supervision": supervision,
    }


def record_correction(commander_message: str, prior_request: str,
                      prior_response: str = "") -> dict:
    """Convenience: log a Commander correction event into Layer 4."""
    return get_correction_memory().log_correction(
        commander_message, prior_request, prior_response
    )


# ─── Demo / manual test ──────────────────────────────────────────────────
if __name__ == "__main__":
    # Simulated end-to-end run with a fake Haiku that hedges,
    # plus a Sonnet escalator that returns clean Hale-tier copy.
    def fake_haiku(substrate, prompt):
        if substrate == "sonnet":
            return "[Sonnet would handle this Hale-tier directly]"
        return "Should I send the email? Let me know if you want me to."

    def fake_sonnet(prompt):
        return "Sent. Logged to dossier. Next sweep at 06:00."

    # Wire fake escalator
    sup = HaleEscalationSupervisor(spawn_fn=fake_sonnet)
    globals()["_supervisor"] = sup

    print("──── HALE-tier request (Layer 1 fires) ────")
    r = dispatch(
        "Hale, should we send the McLeod itinerary today?",
        call_model=fake_haiku,
    )
    print(f"  substrate_used={r['substrate_used']}  escalated={r['escalated']}")
    print(f"  selection.source={r['selection']['source']}")
    print(f"  response={r['response'][:80]}")

    print("\n──── ROUTINE request (default + Layer 3) ────")
    r = dispatch("What time is it in Athens?", call_model=fake_haiku)
    print(f"  substrate_used={r['substrate_used']}  escalated={r['escalated']}")
    print(f"  selection.source={r['selection']['source']}")
    print(f"  supervision={r['supervision']}")
    print(f"  response={r['response'][:80]}")
