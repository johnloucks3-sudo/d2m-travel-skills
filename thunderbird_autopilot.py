"""
Thunderbird Autopilot — Persona Auto-Consultation
===================================================
Event-driven persona consultation. When specific events occur,
automatically consults the right persona panel for advice.

Event Hooks:
  new_booking    → A3 (ops) + A9 (finance) + CH (ethics)
  quote_request  → EXEC (voice) + A5 (strategy) + A6 (narrative)
  payment_due    → A9 (finance) + A3 (ops)
  crisis         → A10 (nuclear) + COS (orchestration)
  client_inquiry → A3 (ops) + EXEC (voice)

Usage:
    from thunderbird_autopilot import consult, EventType
    result = consult(EventType.NEW_BOOKING, "McLeod booked Silver Muse Jun 23-Jul 3")
"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CONSULTATION_LOG = THUNDERBIRD_DIR / "autopilot_log.jsonl"


class EventType(Enum):
    NEW_BOOKING = "new_booking"
    QUOTE_REQUEST = "quote_request"
    PAYMENT_DUE = "payment_due"
    CRISIS = "crisis"
    CLIENT_INQUIRY = "client_inquiry"
    FOLLOW_UP = "follow_up"
    INTEL_ALERT = "intel_alert"


# Which personas to consult for each event type
CONSULTATION_PANELS = {
    EventType.NEW_BOOKING: {
        "personas": ["A3", "A9", "A2", "CH"],
        "label": "Booking Panel",
        "brief": "New booking received. A3 handles ops, A9 checks financials, A2 assesses supplier intel and market positioning, CH flags ethics.",
    },
    EventType.QUOTE_REQUEST: {
        "personas": ["EXEC", "A5", "A6"],
        "label": "Quote Panel",
        "brief": "Quote request. EXEC designs presentation, A5 checks pricing strategy, A6 writes the story.",
    },
    EventType.PAYMENT_DUE: {
        "personas": ["A9", "A3"],
        "label": "Payment Panel",
        "brief": "Payment approaching. A9 verifies amounts, A3 prepares client communication.",
    },
    EventType.CRISIS: {
        "personas": ["A10", "COS"],
        "label": "Crisis Panel",
        "brief": "Crisis activated. A10 fixes, COS orchestrates response.",
    },
    EventType.CLIENT_INQUIRY: {
        "personas": ["A3", "EXEC"],
        "label": "Inquiry Panel",
        "brief": "Client inquiry. A3 handles ops response, EXEC polishes the voice.",
    },
    EventType.FOLLOW_UP: {
        "personas": ["A3", "A9"],
        "label": "Follow-Up Panel",
        "brief": "Follow-up needed. A3 drafts outreach, A9 checks if money is involved.",
    },
    EventType.INTEL_ALERT: {
        "personas": ["A2", "A5"],
        "label": "Intel Panel",
        "brief": "Intelligence alert. A2 analyzes, A5 assesses strategic impact.",
    },
}


def consult(event_type: EventType, context: str,
            use_router: bool = True, log: bool = True) -> dict:
    """Run an auto-consultation panel for an event.

    Args:
        event_type: The type of event triggering consultation
        context: Description of the event/situation
        use_router: If True, use model router (Groq/Claude). If False, just return the plan.
        log: If True, append to consultation log

    Returns:
        dict with panel info and each persona's response
    """
    panel = CONSULTATION_PANELS.get(event_type)
    if not panel:
        return {"error": f"Unknown event type: {event_type}"}

    result = {
        "event": event_type.value,
        "panel": panel["label"],
        "brief": panel["brief"],
        "context": context,
        "timestamp": datetime.now().isoformat(),
        "responses": {},
    }

    if not use_router:
        result["note"] = "Dry run — no API calls made"
        result["personas_would_consult"] = panel["personas"]
        return result

    # Consult each persona via model router
    try:
        from thunderbird_model_router import smart_route
    except ImportError:
        # Fallback to direct persona call
        from thunderbird_personas import call_persona as _call

        def smart_route(pid, query):
            r = _call(pid, query)
            return r

    for pid in panel["personas"]:
        prompt = (
            f"EVENT: {event_type.value.upper()}\n"
            f"PANEL: {panel['label']}\n"
            f"CONTEXT: {context}\n\n"
            f"Provide your assessment and recommended actions. Be specific and actionable."
        )
        try:
            resp = smart_route(pid, prompt)
            result["responses"][pid] = {
                "response": resp.get("response", str(resp)),
                "engine": resp.get("engine", "unknown"),
                "model": resp.get("model", "unknown"),
                "success": resp.get("success", True),
            }
        except Exception as e:
            logger.error(f"Persona {pid} failed: {e}")
            result["responses"][pid] = {
                "response": f"ERROR: {e}",
                "engine": "none",
                "success": False,
            }

    # Log consultation
    if log:
        _log_consultation(result)

    return result


def consult_dry(event_type: EventType, context: str) -> dict:
    """Preview which personas would be consulted without making API calls."""
    return consult(event_type, context, use_router=False, log=False)


def _log_consultation(result: dict):
    """Append consultation result to JSONL log."""
    # Slim version for logging (skip full response text)
    slim = {
        "timestamp": result["timestamp"],
        "event": result["event"],
        "panel": result["panel"],
        "context": result["context"][:200],
        "personas": list(result.get("responses", {}).keys()),
        "all_success": all(
            r.get("success", False) for r in result.get("responses", {}).values()
        ),
    }
    with open(CONSULTATION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(slim) + "\n")


def format_consultation(result: dict) -> str:
    """Format a consultation result for display."""
    lines = [
        f"╔══ {result['panel']} ══╗",
        f"Event: {result['event']}",
        f"Brief: {result['brief']}",
        f"Context: {result['context'][:100]}",
        "─" * 50,
    ]

    for pid, resp in result.get("responses", {}).items():
        status = "✓" if resp.get("success") else "✗"
        engine = resp.get("engine", "?")
        lines.append(f"\n{status} {pid} [{engine}]:")
        lines.append(resp.get("response", "(no response)")[:500])

    lines.append("╚" + "═" * 48 + "╝")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if "--dry" in sys.argv:
        # Dry run all event types
        print("=== AUTOPILOT DRY RUN ===\n")
        for et in EventType:
            result = consult_dry(et, f"Test context for {et.value}")
            panel = CONSULTATION_PANELS[et]
            print(f"{et.value:20s} → {panel['label']:20s} → {', '.join(panel['personas'])}")
        print(f"\n{len(EventType)} event types configured.")
    else:
        # Live test with one event
        print("=== AUTOPILOT LIVE TEST ===")
        print("Testing: NEW_BOOKING event\n")
        result = consult(
            EventType.NEW_BOOKING,
            "Test: McLeod booked Silver Muse Jun 23 - Jul 3, 2026. FPD paid Jan 24."
        )
        print(format_consultation(result))
