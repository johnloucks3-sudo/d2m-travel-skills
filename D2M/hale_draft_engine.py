#!/usr/bin/env python3
"""
hale_draft_engine.py
Dreams2Memories Travel — Thunderbird Wing
Hale's daily touchpoint runner.

Checks all client touchpoint JSON files, finds emails due today or overdue,
extracts the correct template section from .md files, and creates Gmail drafts
in johnloucks3@gmail.com for John to review and send.

Run daily via systemd timer or cron:
  0 7 * * * /usr/bin/python3 /home/john/Thunderbird/D2M/hale_draft_engine.py

Usage:
  python3 hale_draft_engine.py              # Normal daily run
  python3 hale_draft_engine.py --dry-run    # Preview without creating drafts
  python3 hale_draft_engine.py --client kuklinski  # Single client only
  python3 hale_draft_engine.py --force TP-2        # Force-draft a specific touchpoint ID
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

THUNDERBIRD_ROOT    = Path("/home/john/Thunderbird")
TOUCHPOINTS_DIR     = THUNDERBIRD_ROOT / "D2M" / "clients"
TEMPLATE_DIR        = THUNDERBIRD_ROOT / "D2M" / "email_templates"
LOG_FILE            = THUNDERBIRD_ROOT / "logs" / "hale_draft_engine.log"
INBOX_FILE          = THUNDERBIRD_ROOT / "OpsCenter" / "claude_inbox.md"

ADVISOR_EMAIL       = "johnloucks3@gmail.com"
LOOKBACK_DAYS       = 3      # Draft emails this many days overdue (catches weekends)
LOOKAHEAD_DAYS      = 0      # Draft emails this many days ahead (0 = today only)

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("hale_draft_engine")

# ── Gmail Draft Creation ───────────────────────────────────────────────────────

def create_gmail_draft(to: str, subject: str, body: str, dry_run: bool = False) -> str:
    """
    Create a Gmail draft via the D2M-COMMAND-HUB Gmail integration.
    Returns draft ID or 'DRY_RUN'.
    """
    if dry_run:
        log.info(f"  [DRY RUN] Would create draft → {to} | {subject}")
        return "DRY_RUN"

    try:
        # Import D2M Gmail tool — adjust import path to match your hub location
        sys.path.insert(0, str(THUNDERBIRD_ROOT / "D2M-COMMAND-HUB"))
        from gmail_tools import create_draft  # type: ignore

        draft_id = create_draft(
            to=to,
            subject=subject,
            body=body,
            sender=ADVISOR_EMAIL,
        )
        log.info(f"  ✅ Gmail draft created — ID: {draft_id}")
        return draft_id

    except ImportError:
        # Fallback: use Gmail API directly via google-auth
        log.warning("  D2M hub not found — falling back to direct Gmail API")
        return _gmail_api_create_draft(to, subject, body)


def _gmail_api_create_draft(to: str, subject: str, body: str) -> str:
    """Direct Gmail API fallback using service account or OAuth credentials."""
    import base64
    from email.mime.text import MIMEText

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        # Load credentials — adjust path to your OAuth token
        creds_path = THUNDERBIRD_ROOT / "creds" / "gmail_token.json"
        creds = Credentials.from_authorized_user_file(str(creds_path))
        service = build("gmail", "v1", credentials=creds)

        message = MIMEText(body, "plain")
        message["to"] = to
        message["subject"] = subject
        message["from"] = ADVISOR_EMAIL

        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": encoded}}
        ).execute()

        return draft["id"]

    except Exception as e:
        log.error(f"  ❌ Gmail API error: {e}")
        raise


# ── Template Extraction ────────────────────────────────────────────────────────

def extract_template(template_file: str, anchor: str) -> str:
    """
    Extract a named section from a .md template file.
    Anchor matches the first heading line containing the anchor string.
    Returns everything from that heading to the next same-level heading
    (or the next --- divider used between emails in the library).
    """
    template_path = TEMPLATE_DIR / template_file

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")

    # Find the anchor section
    lines = content.split("\n")
    start_idx = None

    for i, line in enumerate(lines):
        if anchor in line:
            start_idx = i
            break

    if start_idx is None:
        raise ValueError(f"Anchor '{anchor}' not found in {template_file}")

    # Extract from anchor to the next major section divider
    # Sections are separated by "---\n\n---" in the arc library
    # or "---" followed by "## PHASE" in timeline touchpoints
    section_lines = []
    in_section = False

    for i, line in enumerate(lines[start_idx:], start=start_idx):
        if i == start_idx:
            in_section = True

        if in_section and i > start_idx:
            # Stop at next section break patterns
            if line.strip() == "---" and i + 2 < len(lines) and lines[i + 2].startswith("---"):
                break
            if line.startswith("## PHASE") and i > start_idx + 5:
                break
            if line.startswith("# ARC") and i > start_idx + 5:
                break
            if line.startswith("# UPDATED TOUCHPOINT"):
                break

        if in_section:
            section_lines.append(line)

    # Strip the markdown headers and metadata lines (###, **Timing:**, **Subject:**)
    # to get the clean email body starting from "Hi Kyle,"
    raw = "\n".join(section_lines)
    return _clean_template_body(raw)


def _clean_template_body(raw: str) -> str:
    """
    Strip markdown headers and template metadata, return clean email body.
    Preserves emoji, bold (**text**), and bullet structure.
    Converts markdown bold to plain text for Gmail plain-text draft.
    """
    lines = raw.split("\n")
    body_lines = []
    in_body = False

    for line in lines:
        # Start capturing from "Hi " — the email greeting
        if line.strip().startswith("Hi "):
            in_body = True

        # Stop at signature block end
        if "www.d2mluxury.quest" in line:
            body_lines.append(line)
            break

        if in_body:
            body_lines.append(line)

    body = "\n".join(body_lines)

    # Light markdown → plain text cleanup (keep structure readable in Gmail)
    body = re.sub(r"\*\*(.+?)\*\*", r"\1", body)   # **bold** → bold
    body = re.sub(r"^\| .+", "", body, flags=re.MULTILINE)  # Remove table rows (need manual fill)
    body = re.sub(r"^\|[-| ]+\|", "", body, flags=re.MULTILINE)  # Remove table separators
    body = re.sub(r"\n{3,}", "\n\n", body)           # Collapse excess blank lines

    return body.strip()


# ── Date Resolution ────────────────────────────────────────────────────────────

def is_due(touchpoint: dict, today: date) -> bool:
    """
    Returns True if a touchpoint should be drafted today.
    - Fixed trigger_date: due if today is within [today - LOOKBACK, today + LOOKAHEAD]
    - null trigger_date: event-driven, never auto-triggered (requires manual flag)
    - status 'sent' or 'skipped': never re-draft
    """
    status = touchpoint.get("status", "pending")
    if status in ("sent", "skipped", "draft_created"):
        return False

    trigger = touchpoint.get("trigger_date")
    if trigger is None:
        return False  # Event-driven — skip in daily run

    trigger_date = date.fromisoformat(trigger)
    window_start = today - timedelta(days=LOOKBACK_DAYS)
    window_end   = today + timedelta(days=LOOKAHEAD_DAYS)

    return window_start <= trigger_date <= window_end


# ── Main Runner ────────────────────────────────────────────────────────────────

def run(dry_run: bool = False, client_filter: str = None, force_id: str = None):
    today = date.today()
    log.info(f"{'='*60}")
    log.info(f"Hale Draft Engine — {today.isoformat()}")
    log.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    log.info(f"{'='*60}")

    # Load client JSON files
    client_files = sorted(TOUCHPOINTS_DIR.glob("*_touchpoints.json"))
    if not client_files:
        log.warning(f"No client touchpoint files found in {TOUCHPOINTS_DIR}")
        return

    total_drafted = 0

    for client_file in client_files:
        client_id = client_file.stem.replace("_touchpoints", "")

        if client_filter and client_id != client_filter:
            continue

        log.info(f"\n📋 Client: {client_id}")

        try:
            data = json.loads(client_file.read_text())
        except json.JSONDecodeError as e:
            log.error(f"  ❌ Invalid JSON in {client_file}: {e}")
            continue

        client_name  = data.get("client_name", client_id)
        client_email = data.get("client_email", "")
        touchpoints  = data.get("touchpoints", [])

        for tp in touchpoints:
            tp_id = tp.get("id", "UNKNOWN")

            # Force mode — draft specific ID regardless of date
            if force_id and tp_id != force_id:
                continue
            elif not force_id and not is_due(tp, today):
                continue

            label    = tp.get("label", tp_id)
            subject  = tp.get("subject", f"[{label}]")
            tmpl     = tp.get("template_file")
            anchor   = tp.get("template_anchor")

            log.info(f"\n  → {tp_id}: {label}")
            log.info(f"    Subject : {subject}")
            log.info(f"    Template: {tmpl} § {anchor}")

            try:
                body = extract_template(tmpl, anchor)
            except (FileNotFoundError, ValueError) as e:
                log.error(f"    ❌ Template error: {e}")
                _write_inbox_alert(client_id, tp_id, label, str(e))
                continue

            # Prepend a Hale header so John knows it's auto-drafted
            header = (
                f"[HALE AUTO-DRAFT — {today.isoformat()}]\n"
                f"Client  : {client_name} <{client_email}>\n"
                f"Touchpt : {tp_id} — {label}\n"
                f"Template: {tmpl} § {anchor}\n"
                f"{'─'*50}\n\n"
            )
            full_body = header + body

            draft_id = create_gmail_draft(
                to=client_email,
                subject=subject,
                body=full_body,
                dry_run=dry_run,
            )

            if not dry_run:
                # Update status in JSON
                tp["status"] = "draft_created"
                tp["draft_id"] = draft_id
                tp["draft_date"] = today.isoformat()
                client_file.write_text(json.dumps(data, indent=2))
                log.info(f"    ✅ Status updated → draft_created")

            total_drafted += 1

    log.info(f"\n{'='*60}")
    log.info(f"Run complete — {total_drafted} draft(s) {'would be ' if dry_run else ''}created")
    log.info(f"{'='*60}\n")


def _write_inbox_alert(client_id: str, tp_id: str, label: str, error: str):
    """Write a failed draft alert to claude_inbox.md for John's attention."""
    if not INBOX_FILE.exists():
        return
    alert = (
        f"\n## ⚠️ HALE DRAFT ENGINE ALERT — {date.today().isoformat()}\n"
        f"- **Client:** {client_id}\n"
        f"- **Touchpoint:** {tp_id} — {label}\n"
        f"- **Error:** {error}\n"
        f"- **Action needed:** Template file or anchor may need updating\n"
    )
    with open(INBOX_FILE, "a") as f:
        f.write(alert)
    log.warning(f"    ⚠️ Alert written to claude_inbox.md")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hale Draft Engine — daily touchpoint email drafter"
    )
    parser.add_argument("--dry-run",  action="store_true", help="Preview without creating drafts")
    parser.add_argument("--client",   help="Run for a single client ID only")
    parser.add_argument("--force",    metavar="TP_ID", help="Force-draft a specific touchpoint ID")
    args = parser.parse_args()

    run(dry_run=args.dry_run, client_filter=args.client, force_id=args.force)
