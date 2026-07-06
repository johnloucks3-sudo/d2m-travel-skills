#!/usr/bin/env python3
"""
booking_notifications.py — Real-time booking lifecycle notifications
======================================================================
Phase 4 communication automation. Fires SMS / push / email-digest
notifications for booking lifecycle events, sourced from Blackboard
client YAML (same source of truth as core/lifecycle/lifecycle_scheduler.py).

Events:
  booking_confirmed      — fired immediately by caller (booking creation flow)
  fpd_due_7days          — scanned daily: final payment date is 7 days out
  embark_countdown_3days — scanned daily: embarkation is 3 days out
  embark_day             — scanned daily: embarkation is today
  post_voyage_24h        — scanned daily: disembarkation was 24h ago

Channels:
  SMS          — Twilio (core.notifications uses the standard Messages API,
                 NOT the wing_sms.py WhatsApp-sandbox path — that path only
                 delivers to numbers that have joined the sandbox, which
                 real clients have not. Standard SMS is subject to the same
                 A2P 10DLC registration status documented in wing_sms.py.)
  PUSH         — Firebase Cloud Messaging via firebase_admin. NOT INSTALLED
                 as of 2026-07-06 (no `firebase_admin` package, no service
                 account configured) — push sends log a "not_configured"
                 status rather than silently succeeding. This is a known
                 capability gap, not a bug: install `firebase-admin` and
                 place a service account JSON at the path in
                 FIREBASE_SERVICE_ACCOUNT_JSON to activate.
  EMAIL_DIGEST — Routed through the existing Gmail draft pipeline
                 (core/email/thunderbird_gmail.py), labeled
                 THUNDERBIRD-Commander-Review, same as every other
                 client-facing email product in this codebase (WF-17).
                 Email digests are never sent directly.

Live-send safety gate:
  SMS and PUSH are transactional, immediate, client-facing sends with no
  human-review step (unlike email, which always drafts). Per the
  wing-wide client-send gate (CLAUDE.md — "no persona, tool, script...
  grants execution authority for client sends"), real sends are OFF by
  default. Set env var D2M_NOTIFICATIONS_LIVE=1 to enable live SMS/push
  sends. With the flag unset, every send is fully exercised (template
  render, opt-in check, ledger write, log entry) but marked
  delivery_status="dry_run_suppressed" instead of calling Twilio/FCM.

Opt-in:
  Read from each client's Blackboard YAML:
    notification_preferences:
      sms_opt_in: true
      push_opt_in: false
      phone: "+17195551234"     # optional override of primary contact phone
      push_token: "..."          # FCM device token
  Missing preferences block or missing per-channel flag = NOT opted in.
  No notification is ever sent to a client who has not explicitly opted in.

Output:
  OpsCenter/logs/notification_log.jsonl — one JSON line per attempted send
    {recipient, channel, event, message, delivery_status, timestamp, ...}
  Blackboard/notification_sent_ledger.json — idempotency ledger for the
    four date-scanned events (prevents re-firing on subsequent daily runs)

Usage:
  from core.notifications.booking_notifications import notify_booking_confirmed
  notify_booking_confirmed("furlow_john_melissa", channels=[Channel.SMS])

  python3 core/notifications/booking_notifications.py --scan --dry-run
  python3 core/notifications/booking_notifications.py --scan --client furlow_john_melissa
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
BLACKBOARD_DIR = THUNDERBIRD_ROOT / "Blackboard" / "clients"
NOTIFICATION_LOG = THUNDERBIRD_ROOT / "OpsCenter" / "logs" / "notification_log.jsonl"
SENT_LEDGER_PATH = THUNDERBIRD_ROOT / "Blackboard" / "notification_sent_ledger.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BOOKING-NOTIF] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)


# ── Env / config ──────────────────────────────────────────────────────────────

def _load_env() -> dict:
    env = dict(os.environ)
    env_file = THUNDERBIRD_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _live_send_enabled(env: dict) -> bool:
    return env.get("D2M_NOTIFICATIONS_LIVE", "0").strip().lower() in ("1", "true", "yes")


# ── Enums ─────────────────────────────────────────────────────────────────────

class NotificationEvent(str, Enum):
    BOOKING_CONFIRMED = "booking_confirmed"
    FPD_DUE_7DAYS = "fpd_due_7days"
    EMBARK_COUNTDOWN_3DAYS = "embark_countdown_3days"
    EMBARK_DAY = "embark_day"
    POST_VOYAGE_24H = "post_voyage_24h"


class Channel(str, Enum):
    SMS = "sms"
    PUSH = "push"
    EMAIL_DIGEST = "email_digest"


# Default channel fan-out per event. Callers may override.
DEFAULT_CHANNELS: dict[NotificationEvent, list[Channel]] = {
    NotificationEvent.BOOKING_CONFIRMED: [Channel.SMS, Channel.PUSH],
    NotificationEvent.FPD_DUE_7DAYS: [Channel.SMS, Channel.EMAIL_DIGEST],
    NotificationEvent.EMBARK_COUNTDOWN_3DAYS: [Channel.SMS, Channel.PUSH],
    NotificationEvent.EMBARK_DAY: [Channel.SMS, Channel.PUSH],
    NotificationEvent.POST_VOYAGE_24H: [Channel.SMS, Channel.EMAIL_DIGEST],
}


# ── Templates ─────────────────────────────────────────────────────────────────
# Placeholders: {first_name} {names} {ship} {voyage_name} {embark_date}
#               {disembark_date} {cabin_number} {balance_due} {supplier}

TEMPLATES: dict[NotificationEvent, dict] = {
    NotificationEvent.BOOKING_CONFIRMED: {
        "sms": "D2M: Great news {first_name} — your {voyage_name} aboard {ship} is CONFIRMED. "
               "Cabin {cabin_number}. We'll be in touch with next steps. — Dreams2Memories Travel",
        "push": {
            "title": "Booking Confirmed!",
            "body": "{voyage_name} aboard {ship} — cabin {cabin_number}. Welcome aboard.",
        },
        "email_subject": "Booking Confirmed — {voyage_name}",
        "email_body": "<p>Dear {names},</p><p>Your reservation aboard the <strong>{ship}</strong> "
                       "is confirmed — cabin {cabin_number}, departing {embark_date}.</p>",
    },
    NotificationEvent.FPD_DUE_7DAYS: {
        "sms": "D2M: Reminder — final payment of {balance_due} for your {voyage_name} voyage is "
               "due in 7 days. Questions? Just reply. — Dreams2Memories Travel",
        "push": {
            "title": "Final Payment Due Soon",
            "body": "{balance_due} due in 7 days for {voyage_name}.",
        },
        "email_subject": "Final Payment Reminder — {voyage_name} (7 Days Out)",
        "email_body": "<p>Dear {first_name},</p><p>Your final payment of <strong>{balance_due}</strong> "
                       "for the {voyage_name} voyage is due in 7 days.</p>",
    },
    NotificationEvent.EMBARK_COUNTDOWN_3DAYS: {
        "sms": "D2M: 3 days until you sail! {voyage_name} aboard {ship} departs {embark_date}. "
               "Travel safe. — Dreams2Memories Travel",
        "push": {
            "title": "3 Days to Go!",
            "body": "{voyage_name} aboard {ship} departs {embark_date}.",
        },
        "email_subject": "3 Days Out — {voyage_name}",
        "email_body": "<p>Dear {names},</p><p>Three days until the {voyage_name} voyage departs "
                       "aboard the {ship}.</p>",
    },
    NotificationEvent.EMBARK_DAY: {
        "sms": "D2M: Welcome aboard, {first_name}! Check your cabin assignment ({cabin_number}) "
               "and enjoy {ship}. — Dreams2Memories Travel",
        "push": {
            "title": "Welcome Aboard!",
            "body": "Check your cabin assignment ({cabin_number}) and enjoy {ship}.",
        },
        "email_subject": "Bon Voyage — {voyage_name}",
        "email_body": "<p>Dear {names},</p><p>Today is the day! Welcome aboard the {ship}.</p>",
    },
    NotificationEvent.POST_VOYAGE_24H: {
        "sms": "D2M: Welcome home! We hope {voyage_name} was unforgettable. We'd love to hear "
               "about it. — Dreams2Memories Travel",
        "push": {
            "title": "Welcome Home",
            "body": "We hope {voyage_name} was unforgettable.",
        },
        "email_subject": "Welcome Home — {voyage_name}",
        "email_body": "<p>Dear {names},</p><p>Welcome home. We hope the {voyage_name} voyage "
                       "aboard the {ship} was everything you imagined.</p>",
    },
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class NotificationPrefs:
    sms_opt_in: bool = False
    push_opt_in: bool = False
    phone: Optional[str] = None
    push_token: Optional[str] = None
    email: Optional[str] = None


@dataclass
class NotificationContext:
    client_id: str
    first_name: str = "Traveler"
    names: str = "Valued Traveler"
    ship: str = "your vessel"
    voyage_name: str = "your voyage"
    embark_date: str = ""
    disembark_date: str = ""
    cabin_number: str = "TBD"
    balance_due: str = ""
    supplier: str = ""

    def as_dict(self) -> dict:
        return {
            "first_name": self.first_name,
            "names": self.names,
            "ship": self.ship,
            "voyage_name": self.voyage_name,
            "embark_date": self.embark_date,
            "disembark_date": self.disembark_date,
            "cabin_number": self.cabin_number,
            "balance_due": self.balance_due,
            "supplier": self.supplier,
        }


# ── Client / booking loading ──────────────────────────────────────────────────

def load_client_yaml(client_id: str) -> Optional[dict]:
    path = BLACKBOARD_DIR / f"{client_id}.yaml"
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def get_prefs(client: dict) -> NotificationPrefs:
    """Resolve notification opt-in/contact info. Absent block = not opted in."""
    prefs_block = client.get("notification_preferences", {}) or {}
    primary = next((c for c in client.get("contacts", []) if c.get("role") == "primary"), {})
    phone = prefs_block.get("phone") or primary.get("phone")
    if phone in ("TBD", "NEEDED", None):
        phone = None
    email = prefs_block.get("email") or primary.get("email")
    if email in ("TBD", "NEEDED", None):
        email = None
    return NotificationPrefs(
        sms_opt_in=bool(prefs_block.get("sms_opt_in", False)),
        push_opt_in=bool(prefs_block.get("push_opt_in", False)),
        phone=phone,
        push_token=prefs_block.get("push_token"),
        email=email,
    )


def build_context(client: dict, booking: Optional[dict] = None) -> NotificationContext:
    names = client.get("client_names", "Valued Traveler")
    first = names.split("&")[0].strip().split()[0] if "&" in names else names.split()[0]
    booking = booking or next(
        (b for b in client.get("bookings", []) if b.get("booking_type") == "cruise"), {}
    )
    return NotificationContext(
        client_id=client.get("client_id", ""),
        first_name=first,
        names=names,
        ship=booking.get("ship", "your vessel") or "your vessel",
        voyage_name=booking.get("voyage_name", "your voyage") or "your voyage",
        embark_date=str(booking.get("embarkation_date", "")),
        disembark_date=str(booking.get("disembarkation_date", "")),
        cabin_number=booking.get("cabin_number", "TBD") or "TBD",
        balance_due=str(booking.get("balance_due", "")),
        supplier=booking.get("supplier", "") or "",
    )


def render(template: str, ctx: NotificationContext) -> str:
    try:
        return template.format(**ctx.as_dict())
    except KeyError as e:
        log.warning(f"Template placeholder missing: {e}")
        return template


# ── Delivery log ──────────────────────────────────────────────────────────────

def log_delivery(entry: dict) -> None:
    NOTIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIFICATION_LOG, "a") as f:
        f.write(json.dumps({**entry, "timestamp": datetime.now(timezone.utc).isoformat()}) + "\n")


# ── Channel senders ────────────────────────────────────────────────────────────

def send_sms(client_id: str, event: NotificationEvent, ctx: NotificationContext, prefs: NotificationPrefs, env: dict) -> dict:
    message = render(TEMPLATES[event]["sms"], ctx)
    base = {"client_id": client_id, "event": event.value, "channel": Channel.SMS.value, "message": message}

    if not prefs.sms_opt_in:
        result = {**base, "recipient": prefs.phone, "delivery_status": "opted_out"}
        log_delivery(result)
        return result
    if not prefs.phone:
        result = {**base, "recipient": None, "delivery_status": "no_recipient"}
        log_delivery(result)
        return result

    if not _live_send_enabled(env):
        result = {**base, "recipient": prefs.phone, "delivery_status": "dry_run_suppressed"}
        log_delivery(result)
        return result

    sid = env.get("TWILIO_ACCOUNT_SID", "")
    token = env.get("TWILIO_AUTH_TOKEN", "")
    from_number = env.get("TWILIO_SMS_NUMBER", "")
    if not sid or not token or not from_number:
        result = {**base, "recipient": prefs.phone, "delivery_status": "not_configured",
                  "error": "Twilio credentials missing from .env"}
        log_delivery(result)
        return result

    try:
        from twilio.rest import Client as TwilioClient

        client = TwilioClient(sid, token)
        msg = client.messages.create(to=prefs.phone, from_=from_number, body=message)
        result = {**base, "recipient": prefs.phone, "delivery_status": msg.status or "sent",
                  "provider_id": msg.sid}
    except Exception as e:
        result = {**base, "recipient": prefs.phone, "delivery_status": "failed", "error": str(e)[:300]}
    log_delivery(result)
    return result


def send_push(client_id: str, event: NotificationEvent, ctx: NotificationContext, prefs: NotificationPrefs, env: dict) -> dict:
    tmpl = TEMPLATES[event]["push"]
    title = render(tmpl["title"], ctx)
    body = render(tmpl["body"], ctx)
    base = {"client_id": client_id, "event": event.value, "channel": Channel.PUSH.value,
            "message": f"{title}: {body}"}

    if not prefs.push_opt_in:
        result = {**base, "recipient": prefs.push_token, "delivery_status": "opted_out"}
        log_delivery(result)
        return result
    if not prefs.push_token:
        result = {**base, "recipient": None, "delivery_status": "no_recipient"}
        log_delivery(result)
        return result

    if not _live_send_enabled(env):
        result = {**base, "recipient": prefs.push_token, "delivery_status": "dry_run_suppressed"}
        log_delivery(result)
        return result

    try:
        import firebase_admin  # noqa: F401
        from firebase_admin import credentials, messaging

        cred_path = env.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
        if not cred_path or not Path(cred_path).exists():
            result = {**base, "recipient": prefs.push_token, "delivery_status": "not_configured",
                      "error": "FIREBASE_SERVICE_ACCOUNT_JSON not set or file missing"}
            log_delivery(result)
            return result

        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        fcm_message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=prefs.push_token,
        )
        msg_id = messaging.send(fcm_message)
        result = {**base, "recipient": prefs.push_token, "delivery_status": "sent", "provider_id": msg_id}
    except ImportError:
        result = {**base, "recipient": prefs.push_token, "delivery_status": "not_configured",
                  "error": "firebase_admin package not installed"}
    except Exception as e:
        result = {**base, "recipient": prefs.push_token, "delivery_status": "failed", "error": str(e)[:300]}
    log_delivery(result)
    return result


def send_email_digest(client_id: str, event: NotificationEvent, ctx: NotificationContext, prefs: NotificationPrefs, env: dict) -> dict:
    """Never sends directly — stages a Gmail draft for Commander review (WF-17),
    same pipeline as core/lifecycle/lifecycle_scheduler.py."""
    tmpl = TEMPLATES[event]
    subject = render(tmpl["email_subject"], ctx)
    body = render(tmpl["email_body"], ctx)
    base = {"client_id": client_id, "event": event.value, "channel": Channel.EMAIL_DIGEST.value,
            "message": subject}

    if not prefs.email:
        result = {**base, "recipient": None, "delivery_status": "no_recipient"}
        log_delivery(result)
        return result

    try:
        sys.path.insert(0, str(THUNDERBIRD_ROOT / "core" / "email"))
        from thunderbird_gmail import gmail_create_draft_sync

        full_html = (
            "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
            "<style>body{font-family:Georgia,serif;background:#f7f3ea;color:#003087;"
            "margin:0;padding:0;}.container{max-width:600px;margin:0 auto;padding:32px 24px;}"
            "p{line-height:1.7;color:#003087;}</style></head><body><div class='container'>"
            f"{body}</div></body></html>"
        )
        draft = gmail_create_draft_sync(to=prefs.email, subject=subject, body=full_html)
        if draft and draft.get("status") == "success":
            result = {**base, "recipient": prefs.email, "delivery_status": "drafted",
                      "provider_id": draft.get("draft_id") or draft.get("message_id")}
        else:
            result = {**base, "recipient": prefs.email, "delivery_status": "failed",
                      "error": "gmail_create_draft_sync returned no success status"}
    except Exception as e:
        result = {**base, "recipient": prefs.email, "delivery_status": "failed", "error": str(e)[:300]}
    log_delivery(result)
    return result


_SENDERS = {
    Channel.SMS: send_sms,
    Channel.PUSH: send_push,
    Channel.EMAIL_DIGEST: send_email_digest,
}


# ── Public trigger API ────────────────────────────────────────────────────────

def fire_event(
    client_id: str,
    event: NotificationEvent,
    booking: Optional[dict] = None,
    channels: Optional[list[Channel]] = None,
    env: Optional[dict] = None,
) -> list[dict]:
    """Fire a notification event for one client across the given (or default) channels."""
    env = env if env is not None else _load_env()
    client = load_client_yaml(client_id)
    if not client:
        result = {"client_id": client_id, "event": event.value, "channel": "n/a",
                  "recipient": None, "delivery_status": "client_not_found", "message": ""}
        log_delivery(result)
        return [result]

    prefs = get_prefs(client)
    ctx = build_context(client, booking)
    channels = channels or DEFAULT_CHANNELS[event]

    results = []
    for ch in channels:
        sender = _SENDERS[ch]
        results.append(sender(client_id, event, ctx, prefs, env))
    return results


def notify_booking_confirmed(client_id: str, booking: Optional[dict] = None,
                              channels: Optional[list[Channel]] = None) -> list[dict]:
    """Call this from the booking-creation flow. Fires immediately, no ledger gate."""
    return fire_event(client_id, NotificationEvent.BOOKING_CONFIRMED, booking, channels)


# ── Idempotency ledger (date-scanned events) ──────────────────────────────────

def load_sent_ledger() -> dict:
    if SENT_LEDGER_PATH.exists():
        try:
            return json.loads(SENT_LEDGER_PATH.read_text())
        except Exception as e:
            log.warning(f"Sent ledger read error (treating as empty): {e}")
    return {}


def _persist_ledger(ledger: dict) -> None:
    SENT_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    SENT_LEDGER_PATH.write_text(json.dumps(ledger, indent=2))


def already_fired(ledger: dict, client_id: str, event: NotificationEvent, check_date: date) -> bool:
    return ledger.get(client_id, {}).get(event.value) == str(check_date)


def mark_fired(ledger: dict, client_id: str, event: NotificationEvent, check_date: date) -> None:
    ledger.setdefault(client_id, {})[event.value] = str(check_date)
    _persist_ledger(ledger)


# ── Daily scan (date-driven events) ───────────────────────────────────────────

def _cruise_booking(client: dict) -> dict:
    return next((b for b in client.get("bookings", []) if b.get("booking_type") == "cruise"), {})


def _parse_date(value) -> Optional[date]:
    if not value or str(value) in ("TBD", "NEEDED", "UNKNOWN", "None", ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def scan_client(client: dict, check_date: date, ledger: dict, dry_run: bool = False, env: Optional[dict] = None) -> list[dict]:
    """Check one client's cruise booking against the four date-driven events."""
    env = env if env is not None else _load_env()
    client_id = client.get("client_id", "")
    booking = _cruise_booking(client)
    embark = _parse_date(booking.get("embarkation_date"))
    disembark = _parse_date(booking.get("disembarkation_date"))
    fpd = _parse_date(booking.get("final_payment_date") or booking.get("fpd"))

    checks = [
        (NotificationEvent.FPD_DUE_7DAYS, fpd, -7),
        (NotificationEvent.EMBARK_COUNTDOWN_3DAYS, embark, -3),
        (NotificationEvent.EMBARK_DAY, embark, 0),
        (NotificationEvent.POST_VOYAGE_24H, disembark, 1),
    ]

    fired: list[dict] = []
    for event, anchor, offset_days in checks:
        if anchor is None:
            continue
        trigger_date = anchor + timedelta(days=offset_days)
        if trigger_date != check_date:
            continue
        if already_fired(ledger, client_id, event, check_date):
            continue

        if dry_run:
            fired.append({"client_id": client_id, "event": event.value, "delivery_status": "dry_run_would_fire"})
            continue

        results = fire_event(client_id, event, booking, env=env)
        fired.extend(results)
        mark_fired(ledger, client_id, event, check_date)

    return fired


def run_daily_scan(check_date: Optional[date] = None, client_filter: Optional[str] = None,
                    dry_run: bool = False) -> dict:
    check_date = check_date or date.today()
    env = _load_env()
    ledger = load_sent_ledger()
    summary = {"date": str(check_date), "processed": 0, "fired": 0, "errors": []}

    if not BLACKBOARD_DIR.exists():
        summary["errors"].append(f"Blackboard directory not found: {BLACKBOARD_DIR}")
        return summary

    client_files = sorted(BLACKBOARD_DIR.glob("*.yaml"))
    if client_filter:
        client_files = [f for f in client_files if client_filter in f.stem]

    for path in client_files:
        try:
            with open(path) as f:
                client = yaml.safe_load(f)
            if not isinstance(client, dict):
                continue
            if client.get("status") not in ("active", "pre_departure"):
                continue
            summary["processed"] += 1
            fired = scan_client(client, check_date, ledger, dry_run=dry_run, env=env)
            summary["fired"] += len(fired)
        except Exception as e:
            summary["errors"].append(f"{path.name}: {str(e)[:150]}")
            log.error(f"Error scanning {path.name}: {e}")

    log.info(f"Daily scan complete: {summary}")
    return summary


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Booking lifecycle notification engine")
    parser.add_argument("--scan", action="store_true", help="Run the daily date-driven event scan")
    parser.add_argument("--dry-run", action="store_true", help="Do not fire notifications, just report what would fire")
    parser.add_argument("--client", help="Filter scan to one client_id")
    parser.add_argument("--date", help="Override check date (YYYY-MM-DD), default=today")
    args = parser.parse_args()

    if not args.scan:
        parser.print_help()
        return

    check_date = date.fromisoformat(args.date) if args.date else date.today()
    summary = run_daily_scan(check_date=check_date, client_filter=args.client, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2, default=str))
    if summary["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
