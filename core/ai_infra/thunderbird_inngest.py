#!/usr/bin/env python3
"""
thunderbird_inngest.py — Inngest event-driven workflow adapter for Thunderbird.
inngest v0.5.x Python SDK. Use for event-triggered workflows: FPD alerts,
client lifecycle triggers, credential refresh events.

Dev server: `npx inngest-cli@latest dev` (UI at http://localhost:8288)
Register app at: http://localhost:8288

Usage:
    from core.ai_infra.thunderbird_inngest import create_inngest_client, create_function

    client = create_inngest_client()

    @client.create_function(
        fn_id="fpd-alert",
        trigger=inngest.TriggerEvent(event="d2m/fpd.approaching"),
    )
    async def handle_fpd_alert(ctx: inngest.Context, step: inngest.Step) -> str:
        booking = await step.run("fetch-booking", lambda: fetch_booking(ctx.event.data))
        await step.run("send-alert", lambda: send_fpd_alert(booking))
        return f"Alerted for {booking['id']}"
"""
from __future__ import annotations
import os
from pathlib import Path

_ENV = Path(__file__).parent.parent.parent / ".env"


def _get_key(name: str) -> str:
    val = os.environ.get(name, "")
    if val:
        return val
    try:
        for line in _ENV.read_text().splitlines():
            if line.startswith(f"{name}=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def create_inngest_client(app_id: str = "thunderbird-wing"):
    """Create an Inngest client. Uses INNGEST_EVENT_KEY from .env (or dev mode if absent)."""
    import inngest
    event_key = _get_key("INNGEST_EVENT_KEY") or "dev"
    return inngest.Inngest(app_id=app_id, event_key=event_key, is_production=bool(_get_key("INNGEST_EVENT_KEY")))


def send_event(event_name: str, data: dict, user_id: str = "thunderbird") -> str:
    """Send an event to Inngest. Returns event ID."""
    import inngest
    client = create_inngest_client()
    ids = client.send_sync(inngest.Event(name=event_name, data=data, user={"id": user_id}))
    return ids[0] if ids else ""


# Standard D2M events
EVENTS = {
    "fpd_approaching":    "d2m/fpd.approaching",      # FPD < 30 days
    "credential_expired": "d2m/credential.expired",    # Portal cookie expired
    "lifecycle_due":      "d2m/lifecycle.tp_due",      # TP past due date
    "client_booked":      "d2m/booking.confirmed",     # New booking confirmed
    "commission_received":"d2m/commission.received",   # Commission hit TESS
}

if __name__ == "__main__":
    print("Inngest dev server should be running at http://localhost:8288")
    print("Start with: npx inngest-cli@latest dev")
    print("Standard D2M events:", list(EVENTS.keys()))
