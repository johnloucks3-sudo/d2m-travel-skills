"""
sms_gateway — texting from the Commander's own number, replacing Telegram.

Google Messages has no official API (research finding, see
docs/TCD_ANDROID_SMS_SETUP.md). The realistic path is an Android-phone
SMS-gateway app (android-sms-gateway / "SMSGate") turning the z-fold6 into
an SMS modem with a local HTTP API, reachable over the Tailscale mesh — real
texts, from the real number, no A2P/10DLC brand wall (it's P2P from a
handset, not carrier A2P).

Two directions:
  * send_sms()   — outbound, via the official ``android_sms_gateway`` PyPI
    client (github.com/android-sms-gateway/client-py), pointed at the
    phone's local-server endpoint instead of the cloud default.
  * poll_inbox() — inbound, via a plain GET against the documented
    ``/inbox`` endpoint. Deliberately polling, not a webhook: a webhook
    would require standing up a NEW hosted listener on this box, which
    directly fights the migration's whole point (retiring the custom web
    tier). Polling needs nothing but an outbound request we already make to
    send.

Config lives in config/sms_gateway_config.json (NOT committed — phone-
specific credentials), created by the Commander after the one-time phone
setup in docs/TCD_ANDROID_SMS_SETUP.md. Every function here raises a clear,
actionable error if that config is missing — same pattern as the existing
Keep/Gmail token-missing errors — rather than silently no-op or guess.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import _imports

ROOT = _imports.ROOT
CONFIG_PATH = ROOT / "config" / "sms_gateway_config.json"


class NotConfigured(RuntimeError):
    pass


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise NotConfigured(
            f"No SMS gateway config at {CONFIG_PATH}.\n"
            "Complete the one-time phone setup first — see "
            "docs/TCD_ANDROID_SMS_SETUP.md — then create this file with:\n"
            '  {"base_url": "http://<phone-tailscale-ip>:8080", '
            '"username": "...", "password": "...", "commander_phone": "+1..."}'
        )
    cfg = json.loads(CONFIG_PATH.read_text())
    for key in ("base_url", "username", "password"):
        if not cfg.get(key):
            raise NotConfigured(f"SMS gateway config missing required field: {key}")
    return cfg


def _client():
    """Official android_sms_gateway APIClient, pointed at the phone's local
    server (not the library's cloud default)."""
    from android_sms_gateway import client
    cfg = _load_config()
    base = cfg["base_url"].rstrip("/")
    return client.APIClient(
        login=cfg["username"], password=cfg["password"],
        base_url=f"{base}/3rdparty/v1",
    )


def send_sms(phone_numbers: list, text: str, *, priority: int = 0) -> dict:
    """Send a real SMS from the phone's real number to ``phone_numbers``.

    Returns {"id": ..., "state": ...} (Pending -> Processed -> Sent ->
    Delivered, or Failed). Raises NotConfigured if the gateway isn't set up
    yet, or the underlying request's own exception on network/auth failure
    (never silently swallowed — a failed send must be visible).
    """
    from android_sms_gateway import domain
    with _client() as c:
        message = domain.Message(
            phone_numbers=phone_numbers,
            text_message=domain.TextMessage(text=text),
            with_delivery_report=True,
            priority=priority,
        )
        response = c.send(message)
        return {"id": response.id, "state": str(response.state)}


def send_alert(text: str) -> dict:
    """Convenience: send to the Commander's own configured number — the
    Telegram-replacement path for push alerts."""
    cfg = _load_config()
    to = cfg.get("commander_phone")
    if not to:
        raise NotConfigured("config missing 'commander_phone' — add the "
                            "Commander's number to send_alert() targets.")
    return send_sms([to], text)


def get_status(message_id: str) -> dict:
    """Poll a previously-sent message's delivery state."""
    with _client() as c:
        status = c.get_state(message_id)
        return {"id": message_id, "state": str(status.state)}


def poll_inbox(limit: int = 50, offset: int = 0, since_iso: str = None) -> list:
    """Recent inbound SMS via GET /inbox (local-server-only endpoint).

    Returns a list of {"id", "sender", "text", "receivedAt"} dicts, newest
    first per the API's own ordering. ``since_iso`` maps to the endpoint's
    ``from`` filter (ISO 8601) when given.
    """
    cfg = _load_config()
    base = cfg["base_url"].rstrip("/")
    params = {"type": "SMS", "limit": limit, "offset": offset}
    if since_iso:
        params["from"] = since_iso
    resp = requests.get(f"{base}/inbox", params=params,
                        auth=(cfg["username"], cfg["password"]), timeout=15)
    resp.raise_for_status()
    raw = resp.json()
    return [{
        "id": m.get("id", ""), "sender": m.get("sender", ""),
        "text": m.get("contentPreview", ""), "receivedAt": m.get("createdAt", ""),
    } for m in raw]


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        print("Testing SMS gateway connection...")
        try:
            cfg = _load_config()
            print(f"Config found: base_url={cfg['base_url']}")
            inbox = poll_inbox(limit=5)
            print(f"Connected. {len(inbox)} recent inbound message(s):")
            for m in inbox:
                print(f"  {m['receivedAt']} — {m['sender']}: {m['text'][:50]}")
        except NotConfigured as e:
            print(f"NOT CONFIGURED: {e}")
        except Exception as e:
            print(f"ERROR: {e}")
    elif "--send" in sys.argv:
        idx = sys.argv.index("--send")
        to, text = sys.argv[idx + 1], sys.argv[idx + 2]
        result = send_sms([to], text)
        print(json.dumps(result, indent=2))
    else:
        print("Usage:")
        print("  python3 -m tcd.sms_gateway --test              # Test connection + show recent inbox")
        print("  python3 -m tcd.sms_gateway --send <phone> <text>  # Send a test SMS")
        print()
        print("Setup: see docs/TCD_ANDROID_SMS_SETUP.md")
