"""
Thunderbird Guest Forms Engine
==============================
Dreams2Memories Travel, LLC

Generates pre-filled Google Form URLs and Gmail drafts for the D2M Guest
Profile form.  Dani-voiced copy, D2M stationery, Commander-review labelled.

Form field IDs must be discovered once per form ID via:
    python3 thunderbird_guest_forms.py --discover <FORM_ID>

Then hardcode them in FORM_FIELD_IDS below.

MCP tool:   generate_guest_form_drafts(client_name, dossier_path=None)
Batch tool: send_all_pending_guest_forms()
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

logger = logging.getLogger("thunderbird_guest_forms")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DOSSIER_DIR = THUNDERBIRD_DIR / "dossiers"
FORM_STATE_FILE = THUNDERBIRD_DIR / "logs" / "guest_forms_sent.json"

# ── Google Form configuration ────────────────────────────────────────────────
# Set FORM_ID once the form has been created via create_guest_profile_form.py.
# Run `python3 thunderbird_guest_forms.py --discover <FORM_ID>` to get field IDs,
# then fill them in below.
FORM_ID: str = ""   # e.g. "1FAIpQLSe..."

# Pre-fill entry IDs — populated after form is live.
# Each key matches the field slug used internally; value is the Google entry ID.
FORM_FIELD_IDS: dict[str, str] = {
    "booking_number": "",      # Booking / Confirmation Number
    "ship_hotel":     "",      # Ship or Hotel Name
    "first_name":     "",      # Legal First Name
    "last_name":      "",      # Legal Last Name
    "email":          "",      # Email
}

# Responder base URL — static
FORM_BASE_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform"

# Days ahead of embarkation to include in batch sweep
BATCH_WINDOW_DAYS = 60

# ---------------------------------------------------------------------------
# Pre-fill URL builder
# ---------------------------------------------------------------------------

def build_prefill_url(
    booking_number: str = "",
    ship_hotel: str = "",
    first_name: str = "",
    last_name: str = "",
    email: str = "",
) -> str:
    """Return a pre-filled Google Form URL for a single guest.

    Any field with an empty entry ID in FORM_FIELD_IDS is silently skipped.
    Falls back to plain form URL if FORM_ID is not set.
    """
    if not FORM_ID:
        return "https://forms.gle/FORM_NOT_CONFIGURED"

    params: dict[str, str] = {}
    values = {
        "booking_number": booking_number,
        "ship_hotel": ship_hotel,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
    }
    for field_key, value in values.items():
        entry_id = FORM_FIELD_IDS.get(field_key, "")
        if entry_id and value:
            params[f"entry.{entry_id}"] = value

    if not params:
        return FORM_BASE_URL

    return f"{FORM_BASE_URL}?{urlencode(params)}&usp=pp_url"


# ---------------------------------------------------------------------------
# Dossier parsing
# ---------------------------------------------------------------------------

def _parse_guests_from_dossier(dossier_path: Path) -> list[dict]:
    """Extract guest name, email, booking ref, ship, and embark date from a dossier.

    Returns a list of dicts:
        { first_name, last_name, email, booking_ref, ship, embark_date }

    Parses the standardised dossier markdown format.  Falls back gracefully
    when fields are missing.
    """
    text = dossier_path.read_text(encoding="utf-8")
    guests: list[dict] = []

    # ── Trip-level fields ────────────────────────────────────────────────────
    ship = ""
    embark_date = ""
    booking_refs: list[str] = []

    for line in text.splitlines():
        # Ship: Silver Muse / SS Grandeur / Viking Mars / etc.
        m = re.search(r"(?:Ship|Vessel)[:\s]+(.+)", line, re.IGNORECASE)
        if m and not ship:
            ship = m.group(1).strip().rstrip(")")

        # Embarkation date — ISO or natural
        m = re.search(r"Embark(?:ation)?[:\s]+(.+)", line, re.IGNORECASE)
        if m and not embark_date:
            embark_date = m.group(1).strip()

        # Confirmation / Booking number
        m = re.search(r"Confirmation\s*#[:\s]+(\S+)", line, re.IGNORECASE)
        if m:
            booking_refs.append(m.group(1).strip())
        m = re.search(r"Booking\s*(?:#|Number|ID)?[:\s]+(\d{5,})", line, re.IGNORECASE)
        if m and m.group(1) not in booking_refs:
            booking_refs.append(m.group(1).strip())

    # ── Per-guest blocks ─────────────────────────────────────────────────────
    # Pattern: lines like "  John Furlow" followed by "Email:" / "Phone:" etc.
    # We scan for blocks that start with a name line and grab the email below.
    name_pattern = re.compile(
        r"^[ \t]+([A-Z][a-z]+(?:\s+\"[^\"]+\")?\s+[A-Z][a-zA-Z\-]+)\s*$"
    )
    email_pattern = re.compile(r"Email[:\s]+([^\s]+@[^\s]+)", re.IGNORECASE)

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        nm = name_pattern.match(lines[i])
        if nm:
            full_name = nm.group(1).strip()
            # Strip nickname e.g. 'Melissa "Missy" Furlow' → first=Melissa last=Furlow
            clean = re.sub(r'"[^"]+"', "", full_name).split()
            if len(clean) >= 2:
                first = clean[0]
                last = clean[-1]
                # Look ahead up to 6 lines for an email
                email = ""
                for j in range(i + 1, min(i + 7, len(lines))):
                    em = email_pattern.search(lines[j])
                    if em:
                        email = em.group(1).strip().rstrip(".")
                        break
                if first and last:
                    guests.append({
                        "first_name": first,
                        "last_name": last,
                        "email": email,
                        "booking_ref": booking_refs[0] if booking_refs else "",
                        "ship": ship,
                        "embark_date": embark_date,
                    })
        i += 1

    # De-duplicate by (first, last) — keep first occurrence
    seen: set[tuple] = set()
    unique: list[dict] = []
    for g in guests:
        key = (g["first_name"].lower(), g["last_name"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(g)

    return unique


def _find_dossier(client_name: str) -> Optional[Path]:
    """Find the best matching dossier for a client name fragment."""
    slug = re.sub(r"[^a-z0-9]", "", client_name.lower())
    for p in DOSSIER_DIR.glob("*.md"):
        if p.name == "CLAUDE.md":
            continue
        if slug in re.sub(r"[^a-z0-9]", "", p.stem.lower()):
            return p
    return None


# ---------------------------------------------------------------------------
# Email body builder (Dani-voiced)
# ---------------------------------------------------------------------------

def _build_email_body(guest: dict, form_url: str) -> str:
    first = guest["first_name"]
    ship = guest.get("ship", "your voyage")
    embark = guest.get("embark_date", "")
    embark_line = f" departing {embark}" if embark else ""

    return f"""\
Dear {first},

We're thrilled about your upcoming adventure{embark_line} aboard {ship} — and we want to make every detail extraordinary.

To help us personalise your experience before you sail, we'd love five minutes of your time to complete your Guest Profile. We've already filled in what we know — just verify, complete a few preferences, and you're done.

Your personalised form is ready here:

{form_url}

This helps us:
  • Ensure your cabin, dining, and excursion preferences are on file
  • Coordinate any special celebrations or milestones
  • Store your loyalty program numbers so you get every point you've earned

If you have any questions at all, please don't hesitate to reach out. We're here for every detail.

With warm regards,
Dani Moreau
Your Luxury Travel Concierge
Dreams2Memories Travel, LLC
concierge@d2mluxury.quest
"""


# ---------------------------------------------------------------------------
# Draft creation
# ---------------------------------------------------------------------------

def create_form_draft(guest: dict) -> dict:
    """Create a single Gmail draft for one guest.  Returns draft metadata."""
    from thunderbird_gmail import gmail_create_draft_sync

    first = guest["first_name"]
    last = guest["last_name"]
    email = guest.get("email", "")
    booking_ref = guest.get("booking_ref", "")
    ship = guest.get("ship", "")

    if not email:
        return {
            "status": "skipped",
            "guest": f"{first} {last}",
            "reason": "no email on file — manual input required",
        }

    form_url = build_prefill_url(
        booking_number=booking_ref,
        ship_hotel=ship,
        first_name=first,
        last_name=last,
        email=email,
    )

    body = _build_email_body(guest, form_url)

    voyage_label = ship if ship else "Your Upcoming Voyage"
    subject = f"Quick Guest Profile — {voyage_label} | {first} {last}"

    try:
        result = gmail_create_draft_sync(
            to=email,
            subject=subject,
            body=body,
            from_address="concierge@d2mluxury.quest",
            label_review=True,
        )
        result["guest"] = f"{first} {last}"
        result["form_url"] = form_url
        _record_form_sent(booking_ref, f"{first} {last}", result.get("draft_id", ""))
        return result
    except Exception as e:
        logger.error(f"Draft creation failed for {first} {last}: {e}")
        return {
            "status": "error",
            "guest": f"{first} {last}",
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Sent-log helpers  (prevents duplicate sends)
# ---------------------------------------------------------------------------

def _load_sent_log() -> dict:
    FORM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if FORM_STATE_FILE.exists():
        try:
            return json.loads(FORM_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _record_form_sent(booking_ref: str, guest_name: str, draft_id: str) -> None:
    log = _load_sent_log()
    key = f"{booking_ref}::{guest_name.lower().replace(' ', '_')}"
    log[key] = {
        "sent_date": date.today().isoformat(),
        "draft_id": draft_id,
        "booking_ref": booking_ref,
        "guest": guest_name,
    }
    FORM_STATE_FILE.write_text(json.dumps(log, indent=2))


def _already_sent(booking_ref: str, guest_name: str) -> bool:
    log = _load_sent_log()
    key = f"{booking_ref}::{guest_name.lower().replace(' ', '_')}"
    return key in log


# ---------------------------------------------------------------------------
# Public API — generate_guest_form_drafts
# ---------------------------------------------------------------------------

def generate_guest_form_drafts(
    client_name: str,
    dossier_path: Optional[str] = None,
    force: bool = False,
) -> dict:
    """Generate pre-filled Guest Profile form drafts for every guest in a booking.

    Args:
        client_name: Client surname or booking key (e.g. "Furlow", "McLeod").
        dossier_path: Absolute path to dossier markdown.  Auto-discovered if None.
        force: Re-send even if forms have already been sent for this booking.

    Returns dict with list of per-guest results and a summary.
    """
    # Resolve dossier
    path: Optional[Path] = None
    if dossier_path:
        path = Path(dossier_path)
    else:
        path = _find_dossier(client_name)

    if not path or not path.exists():
        return {
            "status": "error",
            "error": f"No dossier found for '{client_name}'. Pass dossier_path= explicitly.",
        }

    guests = _parse_guests_from_dossier(path)
    if not guests:
        return {
            "status": "error",
            "error": f"No guests parsed from {path.name}. Check dossier format.",
            "dossier": str(path),
        }

    results = []
    skipped_already_sent = 0
    for guest in guests:
        booking_ref = guest.get("booking_ref", "")
        guest_name = f"{guest['first_name']} {guest['last_name']}"
        if not force and _already_sent(booking_ref, guest_name):
            skipped_already_sent += 1
            results.append({
                "status": "already_sent",
                "guest": guest_name,
                "booking_ref": booking_ref,
            })
            continue
        results.append(create_form_draft(guest))

    success = [r for r in results if r.get("status") == "success"]
    return {
        "status": "complete",
        "dossier": str(path),
        "guests_found": len(guests),
        "drafts_created": len(success),
        "skipped_already_sent": skipped_already_sent,
        "results": results,
    }


# ---------------------------------------------------------------------------
# Batch mode — send_all_pending_guest_forms
# ---------------------------------------------------------------------------

def send_all_pending_guest_forms(window_days: int = BATCH_WINDOW_DAYS) -> dict:
    """Scan all dossiers for bookings departing within window_days and send
    Guest Profile form drafts for any guest who hasn't received one yet.

    Returns a summary across all bookings.
    """
    today = date.today()
    cutoff = today + timedelta(days=window_days)

    # Import KNOWN_BOOKINGS as the authoritative booking list
    from thunderbird_anchor_dates import KNOWN_BOOKINGS

    eligible_keys = []
    for key, bk in KNOWN_BOOKINGS.items():
        embark = bk.get("embark_date")
        if isinstance(embark, date) and today <= embark <= cutoff:
            eligible_keys.append(key)

    if not eligible_keys:
        return {
            "status": "complete",
            "message": f"No bookings departing within {window_days} days.",
            "window_days": window_days,
        }

    all_results = {}
    for key in eligible_keys:
        bk = KNOWN_BOOKINGS[key]
        # Extract client surname from key (e.g. "Furlow_Regent_3071222" → "Furlow")
        surname = key.split("_")[0]
        result = generate_guest_form_drafts(client_name=surname)
        all_results[key] = result

    total_drafts = sum(
        r.get("drafts_created", 0) for r in all_results.values()
    )
    return {
        "status": "complete",
        "bookings_scanned": len(eligible_keys),
        "total_drafts_created": total_drafts,
        "window_days": window_days,
        "per_booking": all_results,
    }


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------

def register_guest_form_tools(mcp) -> None:
    """Register Guest Profile Form tools with the MCP server."""
    from pydantic import Field as PydanticField

    @mcp.tool(
        name="generate_guest_form_drafts",
        annotations={"title": "Generate Guest Profile Form Drafts", "readOnlyHint": False},
    )
    async def _generate_guest_form_drafts_tool(
        client_name: str = PydanticField(
            ...,
            description="Client surname or booking key (e.g. 'Furlow', 'McLeod', 'Kuklinski')",
        ),
        dossier_path: Optional[str] = PydanticField(
            None,
            description="Absolute path to the dossier .md file. Auto-discovered from client_name if omitted.",
        ),
        force: bool = PydanticField(
            False,
            description="Re-create drafts even if guest forms have already been sent for this booking.",
        ),
    ) -> str:
        """Create Gmail drafts with personalised Guest Profile form links for every guest in a booking.

        Reads the dossier to extract guest names, emails, and booking details.
        Builds a pre-filled Google Form URL for each guest.
        Creates one Gmail draft per guest using D2M stationery, Dani-voiced copy.
        All drafts land in the THUNDERBIRD-Commander-Review queue for John's approval before sending.
        """
        result = generate_guest_form_drafts(
            client_name=client_name,
            dossier_path=dossier_path,
            force=force,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(
        name="send_all_pending_guest_forms",
        annotations={"title": "Batch: Send Pending Guest Profile Forms", "readOnlyHint": False},
    )
    async def _send_all_pending_tool(
        window_days: int = PydanticField(
            60,
            description="Look-ahead window in days. Bookings departing within this window get forms.",
        ),
    ) -> str:
        """Sweep all active bookings departing within window_days and create Guest Profile form drafts
        for any guest who hasn't received one yet.

        Skips bookings where forms have already been sent.
        Creates drafts in Commander-review queue — nothing sends until John approves.
        """
        result = send_all_pending_guest_forms(window_days=window_days)
        return json.dumps(result, indent=2, default=str)

    logger.info("Guest Form tools registered: generate_guest_form_drafts, send_all_pending_guest_forms")


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def _discover_field_ids(form_id: str) -> None:
    """Print the pre-fill entry IDs for a Google Form by fetching its JSON metadata.

    Requires the forms_token.json created by create_guest_profile_form.py.
    """
    token_path = THUNDERBIRD_DIR / "forms_token.json"
    if not token_path.exists():
        print(f"ERROR: {token_path} not found. Run create_guest_profile_form.py first.")
        sys.exit(1)

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(token_path))
    svc = build("forms", "v1", credentials=creds)
    form = svc.forms().get(formId=form_id).execute()

    print(f"\nForm: {form['info']['title']}")
    print(f"Form ID: {form_id}")
    print(f"Responder URL: {form.get('responderUri', 'N/A')}\n")
    print("=" * 60)
    print("FIELD IDs — copy into FORM_FIELD_IDS in thunderbird_guest_forms.py")
    print("=" * 60)
    for item in form.get("items", []):
        title = item.get("title", "")
        qi = item.get("questionItem", {}).get("question", {})
        qid = qi.get("questionId", "")
        if qid:
            print(f"  {qid!r:20s}  →  {title}")
    print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="D2M Guest Profile Form Engine")
    subparsers = parser.add_subparsers(dest="cmd")

    disc = subparsers.add_parser("discover", help="Print field IDs for a Google Form")
    disc.add_argument("form_id", help="Google Form ID")

    gen = subparsers.add_parser("generate", help="Generate drafts for a client")
    gen.add_argument("client_name", help="Client surname or booking key")
    gen.add_argument("--dossier", help="Path to dossier .md file", default=None)
    gen.add_argument("--force", action="store_true", help="Re-send even if already sent")

    batch = subparsers.add_parser("batch", help="Send all pending guest forms")
    batch.add_argument("--days", type=int, default=60, help="Look-ahead window in days")

    args = parser.parse_args()

    if args.cmd == "discover":
        _discover_field_ids(args.form_id)
    elif args.cmd == "generate":
        result = generate_guest_form_drafts(args.client_name, args.dossier, args.force)
        print(json.dumps(result, indent=2, default=str))
    elif args.cmd == "batch":
        result = send_all_pending_guest_forms(args.days)
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()
