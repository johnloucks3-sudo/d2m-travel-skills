#!/usr/bin/env python3
"""
hale_send_direct.py — COS Direct Email Sender
==============================================
Dreams2Memories Travel, LLC | Thunderbird Wing

Sends HTML emails directly to any recipient using existing Gmail OAuth.
Bypasses the manual approval workflow for pre-authorized recipients.

Creates drafts in Commander's Gmail (johnloucks3@gmail.com) by default
so you see them in your Drafts folder. Use --from d2mconcierge for the
ops account.

Pilot: Ann Heer (iamheer@ Outlook.com) -> Ron Westbrook extension

Usage:
    python3 hale_send_direct.py --html <file> --to <email> --subject "..."

    python3 hale_send_direct.py --html drafts/heer_processed.html \
        --to iamheer@outlook.com \
        --subject "Your D2M System Access"

    python3 hale_send_direct.py --html drafts/westbrook_proposal.html \
        --to rwestbrook3@gmail.com \
        --subject "Your Mediterranean Cruise Comparison"

    # Draft mode (creates draft, doesn't send):
    python3 hale_send_direct.py --html <file> --to <email> --subject "..." --draft-only

    # Use d2mconcierge account instead of Commander's:
    python3 hale_send_direct.py --html <file> --to <email> --subject "..." --from d2mconcierge

    # Dry run (preview only, no API call):
    python3 hale_send_direct.py --html <file> --to <email> --subject "..." --dry-run

Author: Ms. Victoria "Victory" Hale, SES-6 — Thunderbird Wing Chief of Staff
"""

import argparse
import base64
import json
import logging
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Paths ─────────────────────────────────────────────────────────────────────

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DRAFTS_DIR = THUNDERBIRD_DIR / "drafts"
LOG_DIR = THUNDERBIRD_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Token resolution by account
COMMANDER_TOKEN = THUNDERBIRD_DIR / "creds" / "johnloucks3_token.json"
D2MCONCIERGE_TOKEN = THUNDERBIRD_DIR / "creds" / "gmail_token.json"
if not D2MCONCIERGE_TOKEN.exists():
    D2MCONCIERGE_TOKEN = THUNDERBIRD_DIR / "gmail_token.json"
if D2MCONCIERGE_TOKEN.is_symlink():
    D2MCONCIERGE_TOKEN = D2MCONCIERGE_TOKEN.resolve()

ACCOUNTS = {
    "commander": {
        "token": COMMANDER_TOKEN,
        "email": "johnloucks3@gmail.com",
    },
    "d2mconcierge": {
        "token": D2MCONCIERGE_TOKEN,
        "email": "d2mconcierge@gmail.com",
    },
}

DEFAULT_ACCOUNT = "d2mconcierge"  # SO 27 MAR 2026: send FROM d2mconcierge, not Commander's account

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "hale_send_direct.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("hale_send_direct")

# ── Pre-authorized recipients ─────────────────────────────────────────────────
# Pilot phase: Ann Heer. Extension path: Ron Westbrook + future D2M members.
# Loads from config/authorized_recipients.json if available, with hardcoded defaults.
AUTHORIZED_RECIPIENTS = {
    "iamheer@outlook.com": {
        "name": "Ann Heer",
        "tier": "pilot",
        "note": "System access + Japan trip — Commander's neighbors, complimentary",
    },
    "johnloucks3@gmail.com": {
        "name": "Commander",
        "tier": "member",
        "note": "Commander's email — always authorized",
    },
}
# Merge persisted recipients from JSON file (overrides/adds to defaults)
_persisted_path = THUNDERBIRD_DIR / "config" / "authorized_recipients.json"
if _persisted_path.exists():
    try:
        _persisted = json.loads(_persisted_path.read_text())
        if "recipients" in _persisted:
            AUTHORIZED_RECIPIENTS.update(_persisted["recipients"])
    except Exception:
        pass


# ── Gmail Service ─────────────────────────────────────────────────────────────

def get_gmail_service(account: str = DEFAULT_ACCOUNT) -> tuple:
    """Load Gmail service and sender email for the given account."""
    if account not in ACCOUNTS:
        log.error(f"Unknown account: {account}. Choose from: {', '.join(ACCOUNTS)}")
        sys.exit(1)

    acct = ACCOUNTS[account]
    token_file = acct["token"]
    send_from = acct["email"]

    if not token_file.exists():
        log.error(f"Token not found for '{account}': {token_file}")
        if account == "commander":
            log.error("Commander needs to re-auth via Thunderbird Google OAuth.")
        else:
            log.error("Run: python3 api/thunderbird_google_auth.py --authorize-headless")
        sys.exit(1)

    token_data = json.loads(token_file.read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"]),
    )

    if creds.expired and creds.refresh_token:
        log.info(f"Token expired for '{account}' — refreshing...")
        creds.refresh(Request())
        token_data["token"] = creds.token
        token_data["expiry"] = creds.expiry.isoformat() + "Z"
        token_file.write_text(json.dumps(token_data, indent=2))
        log.info("Token refreshed and saved")

    return build("gmail", "v1", credentials=creds), send_from


# ── Send Email ────────────────────────────────────────────────────────────────

def send_email(service: object, to_email: str, subject: str, html_body: str, send_from: str) -> dict:
    """Send an HTML email via Gmail API. Returns API response."""
    msg = MIMEMultipart("alternative")
    msg["From"] = send_from
    msg["To"] = to_email
    msg["Subject"] = subject

    plain_text = html_body
    for tag in ["<br>", "<br/>", "<br />", "</p>", "</div>", "</li>"]:
        plain_text = plain_text.replace(tag, "\n")
    import re
    plain_text = re.sub(r"<[^>]+>", "", plain_text)
    plain_text = re.sub(r"\n{3,}", "\n\n", plain_text).strip()[:500]

    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()

    return result


# ── Create Draft ──────────────────────────────────────────────────────────────

def create_draft(service: object, to_email: str, subject: str, html_body: str, send_from: str) -> dict:
    """Create a Gmail draft (not sent). Returns API response."""
    msg = MIMEMultipart("alternative")
    msg["From"] = send_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()

    return result


# ── Authorized recipient check ────────────────────────────────────────────────

def is_authorized(email: str) -> bool:
    """Check if recipient is in the pre-authorized list."""
    return email.lower() in {k.lower() for k in AUTHORIZED_RECIPIENTS}


def get_recipient_info(email: str) -> dict:
    """Return recipient profile info."""
    for key, info in AUTHORIZED_RECIPIENTS.items():
        if key.lower() == email.lower():
            return info
    return {"name": email, "tier": "unknown", "note": ""}


# ── Authorize new recipient (extension path) ──────────────────────────────────

def authorize_recipient(email: str, name: str = "", tier: str = "member", note: str = "") -> bool:
    """Add a new recipient to the authorized list (runtime + persistent update).

    Extension path for Ron Westbrook and future D2M members.
    Call this before sending to a new recipient to register them.
    """
    email_lower = email.lower()
    if email_lower in {k.lower() for k in AUTHORIZED_RECIPIENTS}:
        log.info(f"Recipient already authorized: {email}")
        return True

    AUTHORIZED_RECIPIENTS[email] = {
        "name": name or email,
        "tier": tier,
        "note": note,
    }
    _persist_authorized_recipients()
    log.info(f"Authorized new recipient: {name or email} <{email}> [{tier}]")
    return True


def _persist_authorized_recipients():
    """Write authorized recipients to a config file for persistence."""
    config_path = THUNDERBIRD_DIR / "config" / "authorized_recipients.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "meta": {
            "updated": datetime.now().isoformat(),
            "count": len(AUTHORIZED_RECIPIENTS),
        },
        "recipients": AUTHORIZED_RECIPIENTS,
    }
    config_path.write_text(json.dumps(data, indent=2))
    log.info(f"Authorized recipients saved to {config_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Hale Direct Email Sender — send emails from d2mconcierge"
    )
    parser.add_argument("--html", help="Path to HTML email file")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", help="Email subject line")
    parser.add_argument("--from", dest="account", default=DEFAULT_ACCOUNT,
                        help=f"Account to send from: commander (default), d2mconcierge")
    parser.add_argument("--draft-only", action="store_true", help="Create draft instead of sending")
    parser.add_argument("--dry-run", action="store_true", help="Preview without API calls")
    parser.add_argument("--authorize", action="store_true", help="Authorize recipient before sending")
    parser.add_argument("--name", help="Recipient name (for --authorize)")
    parser.add_argument("--tier", default="member", help="Recipient tier (for --authorize): pilot, member, prospect, friend")
    parser.add_argument("--note", default="", help="Internal note about recipient (for --authorize)")
    args = parser.parse_args()

    recipient_email = args.to.strip().lower()

    # ── Authorize mode ─────────────────────────────────────────────────────
    if args.authorize:
        authorize_recipient(
            email=recipient_email,
            name=args.name or "",
            tier=args.tier,
            note=args.note,
        )
        if args.dry_run:
            return 0
        if not args.html and not args.subject:
            log.info(f"Recipient authorized: {recipient_email} ({args.name or recipient_email})")
            log.info("Use without --authorize to send drafts to this recipient.")
            return 0

    # ── Validate send-mode requirements ────────────────────────────────────
    if not args.html or not args.subject:
        log.error("--html and --subject are required for send mode")
        sys.exit(1)

    # ── Check authorization ────────────────────────────────────────────────
    if not is_authorized(recipient_email):
        log.warning(f"Recipient not authorized: {recipient_email}")
        log.warning("Run with --authorize --name \"Name\" --tier <pilot|member|prospect|friend>")
        sys.exit(1)

    recipient_info = get_recipient_info(recipient_email)

    # ── Load HTML ──────────────────────────────────────────────────────────
    html_path = Path(args.html)
    if not html_path.is_absolute():
        html_path = THUNDERBIRD_DIR / args.html
    if not html_path.exists():
        html_path = DRAFTS_DIR / args.html
    if not html_path.exists():
        log.error(f"HTML file not found: {args.html}")
        log.error(f"  Searched: {Path(args.html)}")
        log.error(f"  Searched: {THUNDERBIRD_DIR / args.html}")
        log.error(f"  Searched: {DRAFTS_DIR / args.html}")
        sys.exit(1)

    html_body = html_path.read_text(encoding="utf-8")
    log.info(f"Loaded HTML ({len(html_body):,} bytes)")

    # ── Summary ────────────────────────────────────────────────────────────
    mode = "DRAFT" if args.draft_only else "SEND"
    log.info(f"Mode    : {mode}")
    log.info(f"To      : {recipient_email} ({recipient_info['name']})")
    log.info(f"Subject : {args.subject}")
    log.info(f"Tier    : {recipient_info['tier']}")

    if args.dry_run:
        log.info("Dry run — no API calls made")
        return 0

    # ── Execute ────────────────────────────────────────────────────────────
    service, send_from = get_gmail_service(args.account)

    send_from_name = "Commander" if args.account == "commander" else "D2M Concierge"

    if args.draft_only:
        # Guard: never create a draft to johnloucks3 — Commander doesn't see drafts there
        # SO 27 MAR 2026: internal comms to johnloucks3 are FULL SENDS
        if recipient_email == "johnloucks3@gmail.com":
            log.warning("--draft-only blocked for johnloucks3 (SO 27 MAR 2026: internal comms are direct sends)")
            log.info("Sending directly instead...")
            result = send_email(service, recipient_email, args.subject, html_body, send_from)
            msg_id = result.get("id", "unknown")
            log.info(f"Email sent directly: {msg_id}")
        else:
            result = create_draft(service, recipient_email, args.subject, html_body, send_from)
            draft_id = result.get("id", "unknown")
            log.info(f"Draft created: {draft_id}")
            log.info(f"Draft in {send_from_name}'s Gmail Drafts folder")
            log.info(f"Access: https://mail.google.com/mail/u/0/#drafts")
    else:
        result = send_email(service, recipient_email, args.subject, html_body, send_from)
        msg_id = result.get("id", "unknown")
        log.info(f"Email sent: {msg_id}")
        log.info(f"To: {recipient_info['name']} <{recipient_email}>")
        log.info(f"Sent from: {send_from} ({send_from_name})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
