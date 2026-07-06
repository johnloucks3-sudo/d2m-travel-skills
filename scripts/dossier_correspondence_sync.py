#!/usr/bin/env python3
"""
Dossier Correspondence Sync — Zero-Token Automated Email Logger
Scans sent mail from d2mconcierge + johnloucks3, appends new entries
to client dossier CORRESPONDENCE LOG tables.

Usage:
    python3 scripts/dossier_correspondence_sync.py          # normal run
    python3 scripts/dossier_correspondence_sync.py --dry-run # preview only
    python3 scripts/dossier_correspondence_sync.py --backfill 2026-01-01  # one-time backfill

Runs daily via systemd timer. Zero AI tokens — pure Gmail API + string matching.
"""

import json
import sys
import re
import base64
import email.utils
import logging
import signal
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

OAUTH_REFRESH_TIMEOUT_SEC = 5


class OAuthRefreshTimeout(Exception):
    """Raised when a token refresh hangs past OAUTH_REFRESH_TIMEOUT_SEC."""


def _alarm_handler(signum, frame):
    raise OAuthRefreshTimeout("OAuth refresh exceeded timeout")

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE = Path("/home/john/Thunderbird")
REGISTRY = BASE / "config" / "correspondence_sync_registry.json"
STATE_FILE = BASE / "config" / "correspondence_sync_state.json"
LOG_DIR = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)

TOKENS = {
    "d2mconcierge": BASE / "creds" / "gmail_token.json",
    "johnloucks3": BASE / "creds" / "johnloucks3_token.json",
}

# Exclude these recipient addresses from matching (internal wing addresses)
INTERNAL_ADDRESSES = {
    "johnloucks3@gmail.com",
    "d2mconcierge@gmail.com",
    "concierge@d2mluxury.quest",
}

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "correspondence_sync.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("corr_sync")


def load_gmail_service(token_path: Path):
    """Build Gmail API service from token file.

    Refresh is bounded to OAUTH_REFRESH_TIMEOUT_SEC — a hung refresh (Gmail
    API backoff/rate-limiting) previously blocked forever and crashed the
    whole process (INC-20260612T135256Z-886802). Raises OAuthRefreshTimeout
    or the original exception on failure; caller skips the account.
    """
    token_data = json.loads(token_path.read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"]),
    )
    if creds.expired and creds.refresh_token:
        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(OAUTH_REFRESH_TIMEOUT_SEC)
        try:
            creds.refresh(Request())
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        token_data["token"] = creds.token
        token_data["expiry"] = creds.expiry.isoformat() + "Z" if creds.expiry else None
        token_path.write_text(json.dumps(token_data))
    return build("gmail", "v1", credentials=creds)


def load_registry() -> dict:
    """Load client email registry."""
    data = json.loads(REGISTRY.read_text())
    return data["clients"]


def build_email_index(registry: dict) -> dict:
    """Build reverse index: email_address (lowered) → (client_key, dossier_path, display_name)."""
    index = {}
    for client_key, cfg in registry.items():
        dossier = BASE / cfg["dossier"]
        names = cfg.get("display_names", {})
        for addr in cfg["emails"]:
            addr_lower = addr.lower()
            index[addr_lower] = {
                "client": client_key,
                "dossier": dossier,
                "display": names.get(addr, names.get(addr_lower, addr.split("@")[0])),
            }
    return index


def load_state() -> dict:
    """Load sync state (last run timestamps + processed message IDs)."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_run": {}, "processed_ids": []}


def save_state(state: dict):
    """Persist sync state."""
    # Keep processed_ids from growing unbounded — last 5000
    if len(state.get("processed_ids", [])) > 5000:
        state["processed_ids"] = state["processed_ids"][-5000:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_addresses(header_value: str) -> list[str]:
    """Parse email addresses from a To/CC/BCC header."""
    if not header_value:
        return []
    addresses = []
    for _name, addr in email.utils.getaddresses([header_value]):
        if addr:
            addresses.append(addr.lower())
    return addresses


def fetch_sent_messages(service, after_date: str) -> list[dict]:
    """Fetch sent messages after a given date. Returns list of {id, subject, to, cc, bcc, date}."""
    query = f"in:sent after:{after_date}"
    messages = []
    page_token = None

    while True:
        resp = service.users().messages().list(
            userId="me", q=query, maxResults=100, pageToken=page_token
        ).execute()

        for msg_stub in resp.get("messages", []):
            msg = service.users().messages().get(
                userId="me", id=msg_stub["id"], format="metadata",
                metadataHeaders=["To", "Cc", "Bcc", "Subject", "Date"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            messages.append({
                "id": msg_stub["id"],
                "subject": headers.get("Subject", "(no subject)"),
                "to": headers.get("To", ""),
                "cc": headers.get("Cc", ""),
                "bcc": headers.get("Bcc", ""),
                "date_raw": headers.get("Date", ""),
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return messages


def parse_date(date_raw: str) -> Optional[str]:
    """Parse RFC 2822 date to YYYY-MM-DD."""
    try:
        parsed = email.utils.parsedate_to_datetime(date_raw)
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def match_message_to_clients(msg: dict, email_index: dict) -> list[dict]:
    """Match a sent message to client dossiers. Returns list of matches."""
    all_recipients = set()
    for field in ("to", "cc", "bcc"):
        all_recipients.update(extract_addresses(msg[field]))

    # Remove internal addresses
    external = all_recipients - INTERNAL_ADDRESSES

    # Match against registry
    matches = {}  # dossier_path → {client, recipients, display_names}
    for addr in external:
        if addr in email_index:
            info = email_index[addr]
            dossier_str = str(info["dossier"])
            if dossier_str not in matches:
                matches[dossier_str] = {
                    "client": info["client"],
                    "dossier": info["dossier"],
                    "recipients": [],
                }
            matches[dossier_str]["recipients"].append(info["display"])

    return list(matches.values())


def format_log_entry(date: str, subject: str, recipients: list[str], account: str) -> str:
    """Format a correspondence log table row."""
    to_str = ", ".join(sorted(set(recipients)))
    # Truncate very long subjects
    if len(subject) > 100:
        subject = subject[:97] + "..."
    # Escape pipe characters in subject
    subject = subject.replace("|", "\\|")
    # Add account indicator if from johnloucks3
    if account == "johnloucks3":
        to_str += " (from personal)"
    return f"| {date} | {subject} | {to_str} |"


def find_correspondence_log_insertion_point(content: str) -> Optional[int]:
    """Find where to insert new rows in the CORRESPONDENCE LOG table.
    Returns the character index of the line AFTER the last table row,
    or None if no correspondence log section found."""
    # Find the correspondence log header
    pattern = r"### CORRESPONDENCE LOG — Outbound to Clients"
    match = re.search(pattern, content)
    if not match:
        return None

    # Find the table — skip header row and separator
    # Look for the last table row (starts with |)
    lines = content[match.start():].split("\n")
    last_table_line_offset = None
    in_table = False

    offset = match.start()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            last_table_line_offset = offset + len(line) + 1  # +1 for newline
        elif in_table and not stripped.startswith("|") and stripped != "":
            # End of table
            break
        offset += len(line) + 1

    return last_table_line_offset


def append_to_dossier(dossier_path: Path, entries: list[str], dry_run: bool = False) -> int:
    """Append correspondence entries to dossier file. Returns count appended."""
    if not dossier_path.exists():
        log.warning(f"Dossier not found: {dossier_path}")
        return 0

    content = dossier_path.read_text()
    insert_at = find_correspondence_log_insertion_point(content)

    if insert_at is None:
        log.warning(f"No CORRESPONDENCE LOG section in {dossier_path.name} — skipping")
        return 0

    new_rows = "\n".join(entries) + "\n"

    if dry_run:
        log.info(f"  [DRY RUN] Would append {len(entries)} rows to {dossier_path.name}")
        for e in entries:
            log.info(f"    {e}")
        return len(entries)

    updated = content[:insert_at] + new_rows + content[insert_at:]
    dossier_path.write_text(updated)
    log.info(f"  Appended {len(entries)} rows to {dossier_path.name}")
    return len(entries)


def run_sync(dry_run: bool = False, backfill_date: Optional[str] = None):
    """Main sync loop."""
    registry = load_registry()
    email_index = build_email_index(registry)
    state = load_state()
    processed = set(state.get("processed_ids", []))
    now = datetime.now(timezone.utc)

    total_new = 0
    # Accumulate entries per dossier to batch-write
    dossier_entries: dict[str, list[str]] = {}

    for account_name, token_path in TOKENS.items():
        if not token_path.exists():
            log.warning(f"Token missing for {account_name}: {token_path}")
            continue

        log.info(f"Scanning {account_name}...")
        try:
            service = load_gmail_service(token_path)
        except Exception as exc:
            log.error(f"  Skipping {account_name}: OAuth refresh failed ({exc})")
            continue

        # Determine start date
        if backfill_date:
            after = backfill_date
        else:
            last = state.get("last_run", {}).get(account_name)
            if last:
                # Go back 2 days for safety overlap
                dt = datetime.fromisoformat(last)
                after = (dt - timedelta(days=2)).strftime("%Y/%m/%d")
            else:
                # First run: last 7 days
                after = (now - timedelta(days=7)).strftime("%Y/%m/%d")

        log.info(f"  Fetching sent mail after {after}")
        try:
            messages = fetch_sent_messages(service, after)
        except Exception as exc:
            log.error(f"  Skipping {account_name}: message fetch failed ({exc})")
            continue
        log.info(f"  Found {len(messages)} sent messages")

        for msg in messages:
            if msg["id"] in processed:
                continue

            matches = match_message_to_clients(msg, email_index)
            if not matches:
                continue

            date_str = parse_date(msg["date_raw"])

            for match in matches:
                dossier_key = str(match["dossier"])
                entry = format_log_entry(
                    date_str, msg["subject"], match["recipients"], account_name
                )
                if dossier_key not in dossier_entries:
                    dossier_entries[dossier_key] = []
                dossier_entries[dossier_key].append((date_str, entry))

            processed.add(msg["id"])
            total_new += 1

        # Update last run timestamp
        state.setdefault("last_run", {})[account_name] = now.isoformat()

    # Sort entries by date and write to dossiers
    for dossier_key, entries in dossier_entries.items():
        entries.sort(key=lambda x: x[0])  # sort by date
        rows = [e[1] for e in entries]
        dossier_path = Path(dossier_key)
        append_to_dossier(dossier_path, rows, dry_run=dry_run)

    # Save state
    state["processed_ids"] = list(processed)
    if not dry_run:
        save_state(state)

    log.info(f"Sync complete. {total_new} new client emails logged across {len(dossier_entries)} dossiers.")
    return total_new


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    backfill = None
    for i, arg in enumerate(sys.argv):
        if arg == "--backfill" and i + 1 < len(sys.argv):
            backfill = sys.argv[i + 1]

    if dry_run:
        log.info("=== DRY RUN MODE ===")
    if backfill:
        log.info(f"=== BACKFILL from {backfill} ===")

    run_sync(dry_run=dry_run, backfill_date=backfill)
