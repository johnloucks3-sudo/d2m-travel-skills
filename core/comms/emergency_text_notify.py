#!/usr/bin/env python3
"""
emergency_text_notify.py — manually-armed emergency text channel. Uses
WhatsApp (already live, no A2P 10DLC carrier registration needed) rather
than voice.

NOT auto-wired into any escalation path. Commander directive 2026-07-10:
"DO NOT call me at all... I will set up Emergency calling when needed and
I am out of town, etc." Voice was found to over-fire on every client-
affecting P0 -- removed from core/notify/hale_notify.py entirely. This
module exists as a dormant, callable-on-purpose capability only.

Real carrier SMS was tested live 2026-07-10 and is still blocked (Twilio
error 30034, A2P 10DLC unregistered -- no brand registration exists at all,
not just "pending"). WhatsApp is the working substitute: delivers to
Google Messages on Android, same UX as native SMS.

Usage:
    from core.comms.emergency_text_notify import emergency_text
    result = emergency_text("Regent portal down, client-affecting.")
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.comms.wing_sms import send_sms, COMMANDER_PHONE

THUNDERBIRD = Path(__file__).parent.parent.parent
LOG_FILE = THUNDERBIRD / "logs" / "emergency_text_notify.log"


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def emergency_text(message: str, to: str = COMMANDER_PHONE) -> dict:
    """Send an emergency text via WhatsApp (falls back to SMS if it ever
    clears 10DLC registration -- send_sms already handles that fallback).
    Never raises. Returns {"sent": bool} -- caller decides what "sent=False"
    means for further escalation, this function does not retry or call
    another channel itself."""
    try:
        ok = send_sms(message, to=to)
        _log(f"to={to} sent={ok} message={message[:100]!r}")
        return {"sent": ok}
    except Exception as e:
        _log(f"FAILED to={to}: {e}")
        return {"sent": False, "error": str(e)}


if __name__ == "__main__":
    import sys
    msg = sys.argv[1] if len(sys.argv) > 1 else "Thunderbird Wing emergency text channel test."
    print(emergency_text(msg))
