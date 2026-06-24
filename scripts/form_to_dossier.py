#!/usr/bin/env python3
"""
form_to_dossier.py — Google Form Response → Client Dossier Auto-Ingest
MISSION-434 · ELON (A12) · 2026-06-24

Polls the Google Sheet linked to the D2M onboarding/preference form.
For each new response: creates or updates the client's dossier markdown.
Telegrams Commander on ingestion.

Usage:
    python3 scripts/form_to_dossier.py [--once] [--dry-run]

    --once:    run once and exit (no polling loop)
    --dry-run: parse responses, print what would be written, don't write

Schedule: run via cron or systemd timer every 15 minutes.

Form ID:  1Ni_MKR8gqfpVVlaNt3RUBfDFd4hcy4U5SSTse4RUpo8
Auth:     d2mconcierge OAuth token (config/persona_gmail_token.json)
          Requires: https://www.googleapis.com/auth/spreadsheets.readonly
                    https://www.googleapis.com/auth/drive.readonly
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Config ────────────────────────────────────────────────────────────────────

FORM_ID = "1Ni_MKR8gqfpVVlaNt3RUBfDFd4hcy4U5SSTse4RUpo8"
DOSSIERS_DIR = ROOT / "dossiers"
STATE_FILE = ROOT / "logs" / "form_to_dossier_state.json"
POLL_INTERVAL_SECONDS = 900  # 15 minutes
TOKEN_FILE = ROOT / "config" / "persona_gmail_token.json"

# Column name normalization — maps raw Google Form header → dossier field
FIELD_MAP = {
    "timestamp": "form_submitted_at",
    "email address": "email",
    "first name": "first_name",
    "last name": "last_name",
    "full name": "full_name",
    "phone": "phone",
    "phone number": "phone",
    "travel preferences": "preferences_raw",
    "destination interests": "destination_interests",
    "cabin preference": "cabin_preference",
    "dietary restrictions": "dietary",
    "dietary needs": "dietary",
    "special requests": "special_requests",
    "travel party size": "party_size",
    "budget range": "budget_range",
    "preferred departure": "preferred_departure",
    "travel dates": "preferred_departure",
    "anniversary": "anniversary",
    "birthday": "birthday",
    "cruise line preference": "cruise_line_preference",
    "how did you hear": "referral_source",
    "referral": "referral_source",
    "comments": "notes",
    "additional notes": "notes",
}


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_sheets_service():
    """Build an authorized Google Sheets service using the d2mconcierge token."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: google-api-python-client not installed.")
        print("Run: pip install google-api-python-client google-auth-oauthlib")
        sys.exit(1)

    token_data = json.loads(TOKEN_FILE.read_text())

    creds = Credentials(
        token=token_data.get("access_token") or token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("sheets", "v4", credentials=creds, cache_discovery=False)


# ── Sheets helpers ────────────────────────────────────────────────────────────

def find_linked_sheet(drive_service, form_id: str) -> str | None:
    """
    Google Forms automatically creates a linked Responses spreadsheet.
    Search Drive for it by name pattern or linked form property.
    """
    try:
        result = drive_service.files().list(
            q=f"mimeType='application/vnd.google-apps.spreadsheet' and name contains 'Form Responses'",
            fields="files(id,name,createdTime)",
            orderBy="createdTime desc",
            pageSize=10,
        ).execute()
        files = result.get("files", [])
        if files:
            return files[0]["id"]
    except Exception as e:
        print(f"Drive search failed: {e}")
    return None


def get_sheet_rows(service, spreadsheet_id: str) -> tuple[list[str], list[dict]]:
    """Return (headers, rows) from the first sheet tab."""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="A1:ZZ",
    ).execute()

    values = result.get("values", [])
    if not values:
        return [], []

    headers = [h.strip().lower() for h in values[0]]
    rows = []
    for i, row in enumerate(values[1:], start=2):
        # Pad short rows
        padded = row + [""] * (len(headers) - len(row))
        rows.append({"_row_number": i, **dict(zip(headers, padded))})

    return headers, rows


# ── State tracking ────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed_rows": [], "spreadsheet_id": None, "last_run": None}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Field normalization ───────────────────────────────────────────────────────

def normalize_row(raw: dict) -> dict:
    """Map raw form column headers to dossier field names."""
    result = {}
    for raw_key, value in raw.items():
        if raw_key.startswith("_"):
            result[raw_key] = value
            continue
        normalized_key = FIELD_MAP.get(raw_key, raw_key.replace(" ", "_"))
        result[normalized_key] = value
    return result


def extract_client_name(row: dict) -> str:
    """Best-effort client name from form response."""
    if row.get("full_name"):
        return row["full_name"].strip()
    first = row.get("first_name", "").strip()
    last = row.get("last_name", "").strip()
    if first and last:
        return f"{first} {last}"
    if first:
        return first
    if row.get("email"):
        return row["email"].split("@")[0].replace(".", " ").title()
    return f"FormResponse_{row.get('_row_number', 'unknown')}"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# ── Dossier write ─────────────────────────────────────────────────────────────

def find_existing_dossier(client_name: str, email: str) -> Path | None:
    """Try to find an existing dossier by name or email match."""
    name_parts = client_name.lower().split()
    for dossier in DOSSIERS_DIR.glob("*.md"):
        fname = dossier.name.lower()
        if email and email.lower() in dossier.read_text().lower():
            return dossier
        if any(part in fname for part in name_parts if len(part) > 3):
            return dossier
    return None


def build_dossier_section(row: dict, client_name: str) -> str:
    """Build the ## FORM RESPONSES section to append/update in a dossier."""
    ts = row.get("form_submitted_at", datetime.now(timezone.utc).isoformat())
    lines = [
        f"\n## FORM RESPONSES (auto-ingested {ts})\n",
        f"*Source: D2M Onboarding/Preference Form · Row {row.get('_row_number', '?')}*\n",
    ]

    skip_fields = {"_row_number", "form_submitted_at", "full_name", "first_name", "last_name"}
    for key, value in row.items():
        if key in skip_fields or not value:
            continue
        label = key.replace("_", " ").title()
        lines.append(f"- **{label}:** {value}")

    lines.append(f"\n*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n")
    return "\n".join(lines)


def create_new_dossier(client_name: str, row: dict) -> Path:
    """Create a minimal dossier stub for a brand-new client."""
    slug = slugify(client_name)
    path = DOSSIERS_DIR / f"{slug}_form_intake.md"

    email = row.get("email", "")
    phone = row.get("phone", "")

    frontmatter = f"""---
client: {client_name}
full_name: {client_name}
email: {email}
phone: {phone}
status: prospect
relationship: prospect
source: google_form
form_intake_date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
---
# CLIENT DOSSIER — {client_name}
*Auto-created from Google Form intake {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*

"""
    path.write_text(frontmatter + build_dossier_section(row, client_name))
    return path


def update_existing_dossier(path: Path, row: dict, client_name: str) -> Path:
    """Append/replace the FORM RESPONSES section in an existing dossier."""
    content = path.read_text()
    section = build_dossier_section(row, client_name)

    # Replace existing FORM RESPONSES section if present
    pattern = r"\n## FORM RESPONSES.*?(?=\n## |\Z)"
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, section, content, flags=re.DOTALL)
    else:
        content = content.rstrip() + "\n" + section

    path.write_text(content)
    return path


# ── Telegram notification ─────────────────────────────────────────────────────

def telegram_notify(client_name: str, dossier_path: Path, is_new: bool):
    """Send Telegram page to Commander via D2MC2C bot."""
    action = "CREATED" if is_new else "UPDATED"
    msg = (
        f"FORM INGEST — {action}\n"
        f"Client: {client_name}\n"
        f"Dossier: {dossier_path.name}\n"
        f"Source: D2M Onboarding Form\n"
        f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )

    # Use the Thunderbird telegram gateway
    gw_script = ROOT / "OpsCenter" / "thunderbird_telegram_gw.py"
    if gw_script.exists():
        import subprocess
        subprocess.run(
            ["python3", str(gw_script), "--send", msg],
            capture_output=True,
            timeout=10,
        )
    else:
        print(f"[TELEGRAM] {msg}")


# ── Main loop ─────────────────────────────────────────────────────────────────

def process_responses(dry_run: bool = False) -> list[str]:
    """Check for new form responses and ingest them. Returns list of ingested client names."""
    state = load_state()

    try:
        service = get_sheets_service()
    except Exception as e:
        print(f"Auth failed: {e}")
        return []

    # Resolve spreadsheet ID — check state first, then search Drive
    spreadsheet_id = state.get("spreadsheet_id")
    if not spreadsheet_id:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            token_data = json.loads(TOKEN_FILE.read_text())
            creds = Credentials(
                token=token_data.get("access_token") or token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
            )
            drive_svc = build("drive", "v3", credentials=creds, cache_discovery=False)
            spreadsheet_id = find_linked_sheet(drive_svc, FORM_ID)
        except Exception as e:
            print(f"Drive search failed: {e}")

    if not spreadsheet_id:
        print("ERROR: Could not locate the linked Google Sheets spreadsheet.")
        print("Set SHEETS_ID env var or manually populate state file.")
        print(f"State file: {STATE_FILE}")
        return []

    state["spreadsheet_id"] = spreadsheet_id

    try:
        headers, rows = get_sheet_rows(service, spreadsheet_id)
    except Exception as e:
        print(f"Sheets read failed: {e}")
        return []

    processed = set(state.get("processed_rows", []))
    ingested = []

    for row in rows:
        row_num = row["_row_number"]
        if row_num in processed:
            continue

        normalized = normalize_row(row)
        client_name = extract_client_name(normalized)
        email = normalized.get("email", "")

        print(f"New response — Row {row_num}: {client_name} <{email}>")

        if not dry_run:
            existing = find_existing_dossier(client_name, email)
            if existing:
                path = update_existing_dossier(existing, normalized, client_name)
                is_new = False
                print(f"  Updated: {path.name}")
            else:
                path = create_new_dossier(client_name, normalized)
                is_new = True
                print(f"  Created: {path.name}")

            telegram_notify(client_name, path, is_new)
            processed.add(row_num)
            ingested.append(client_name)
        else:
            print(f"  [DRY-RUN] Would {'create' if not find_existing_dossier(client_name, email) else 'update'} dossier for {client_name}")

    if not dry_run:
        state["processed_rows"] = sorted(processed)
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        save_state(state)

    return ingested


def main():
    parser = argparse.ArgumentParser(description="Form-to-Dossier pipeline")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't write")
    args = parser.parse_args()

    print(f"[form_to_dossier] Starting — Form ID: {FORM_ID}")
    print(f"[form_to_dossier] Dossiers dir: {DOSSIERS_DIR}")

    if args.once or args.dry_run:
        ingested = process_responses(dry_run=args.dry_run)
        print(f"Done. Ingested: {ingested or 'none (no new responses)'}")
        return

    print(f"[form_to_dossier] Polling every {POLL_INTERVAL_SECONDS}s. Ctrl+C to stop.")
    while True:
        try:
            ingested = process_responses()
            if ingested:
                print(f"Ingested: {ingested}")
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
