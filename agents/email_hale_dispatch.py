#!/usr/bin/env python3
"""
email_hale_dispatch.py — Email tasking handler wired to the Hale Dispatcher Runtime.

Processes incoming Commander emails-as-task-instructions through the substrate-aware
dispatch chain (Layer 1 keyword classification → Layer 4 correction memory → model
call → Layer 3 supervision → telemetry).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTEGRATION HOOK for OpsCenter/email_task_ingest.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In email_task_ingest.py's route_task() function, add before the existing
persona-based routing for "hale" (or as an early-exit when substrate is
Hale-tier):

    # ── Hale dispatcher integration (add before existing if/elif chain) ──
    from agents.email_hale_dispatch import handle_email_task, is_hale_tier_email
    if is_hale_tier_email(subject, body):
        result = handle_email_task(subject=subject, body=body, sender=sender)
        # result["response"] is the Hale model output
        # Log it to the wing comms or mission board as needed
        logging.info(
            "[EMAIL INGEST] Hale dispatcher handled: substrate=%s savings=$%.4f",
            result["substrate_used"],
            result["telemetry"].get("savings_usd", 0),
        )
        return  # task handled — skip legacy routing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path("/home/john/Thunderbird")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "OpsCenter") not in sys.path:
    sys.path.insert(0, str(_ROOT / "OpsCenter"))

from agents.hale_substrate_chain import select_substrate
from agents.hale_dispatcher_runtime import dispatch_with_telemetry


def is_hale_tier_email(subject: str, body: str) -> bool:
    """Return True if the email subject+body warrants Hale-tier routing.

    Fast classification — no model call. Uses Layer 1/4 substrate chain.
    """
    request = _build_request(subject, body, sender="")
    sel = select_substrate(request)
    return sel["substrate"] in ("sonnet", "opus")


def handle_email_task(subject: str, body: str, sender: str) -> dict:
    """Process a Commander email task through the Hale Dispatcher Runtime.

    Combines subject + body into a unified request, runs substrate selection,
    dispatches to the appropriate model (Sonnet/Opus via MAX OAuth or Haiku),
    and logs telemetry.

    Args:
        subject: Email subject line (often contains [TAG] or task keyword).
        body: Email body text.
        sender: Sender email address (for audit trail; not routed to models).

    Returns:
        Dict with:
          response (str):        Model output from Hale.
          substrate_used (str):  "sonnet" | "opus" | "haiku".
          telemetry (dict):      Full telemetry record (cost, savings, substrate, etc.).
          selection (dict):      Layer 1/4 classification result.
    """
    request = _build_request(subject, body, sender)
    result = dispatch_with_telemetry(request, default_substrate="haiku")
    return {
        "response": result["response"],
        "substrate_used": result["substrate_used"],
        "telemetry": result["telemetry"],
        "selection": result["selection"],
    }


def _build_request(subject: str, body: str, sender: str) -> str:
    """Compose a unified request string from email fields."""
    parts = []
    if sender:
        parts.append(f"Email from: {sender}")
    if subject:
        parts.append(f"Subject: {subject}")
    if body:
        parts.append(f"\n{body.strip()}")
    return "\n".join(parts)
