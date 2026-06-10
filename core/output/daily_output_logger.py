"""
Daily Output Logger — Drive Mirror Pipeline
Dreams2Memories Travel, LLC · A7 Sterling build · 2026-06-10

Any Wing script that produces a work product calls log_output() to:
  1. Upload the file to Google Drive folder Thunderbird/Daily Outputs/YYYY-MM-DD/
  2. Retrieve the Drive share link
  3. Append an entry to OpsCenter/daily_output_log.json

The brief reads daily_output_log.json at 0555 and inserts links into
the Yesterday's Outputs section.

FAIL-SOFT GUARANTEE: If Drive upload fails for any reason, the entry
is still written to daily_output_log.json with drive_link=null and
local_path preserved. A Drive hiccup MUST NOT block the 0600 send.

Drive auth: uses drive_token.json (OAuth, full drive scope).
Refreshes automatically via google-auth-oauthlib flow.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("daily_output_logger")

# ── PATHS ─────────────────────────────────────────────────────────────────────
THUNDERBIRD_DIR = Path.home() / "Thunderbird"
OUTPUT_LOG_PATH = THUNDERBIRD_DIR / "OpsCenter" / "daily_output_log.json"
DRIVE_TOKEN_PATH = THUNDERBIRD_DIR / "creds" / "drive_token.json"
DRIVE_OAUTH_CREDS_PATH = THUNDERBIRD_DIR / "creds" / "credentials.json"

# Drive folder name structure
DRIVE_ROOT_FOLDER_NAME = "Thunderbird"
DRIVE_DAILY_PARENT = "Daily Outputs"

# OAuth scopes required
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


# ── DRIVE SERVICE ─────────────────────────────────────────────────────────────

def _get_drive_service():
    """Return an authenticated Google Drive v3 service using drive_token.json."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        if DRIVE_TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(DRIVE_TOKEN_PATH), DRIVE_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Persist refreshed token
                DRIVE_TOKEN_PATH.write_text(creds.to_json())
            else:
                raise RuntimeError(
                    "Drive token missing or invalid and cannot refresh. "
                    f"Re-authorize via: python3 {__file__} --authorize"
                )

        return build("drive", "v3", credentials=creds)

    except Exception as e:
        raise RuntimeError(f"Drive service unavailable: {e}") from e


# ── FOLDER RESOLUTION ─────────────────────────────────────────────────────────

def _find_or_create_folder(service, name: str, parent_id: Optional[str] = None) -> str:
    """Find a Drive folder by name (under optional parent), or create it.

    Returns the folder ID.
    """
    q = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"

    result = service.files().list(q=q, fields="files(id, name)", pageSize=5).execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]

    # Create folder
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        meta["parents"] = [parent_id]

    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def _get_daily_folder_id(service, date_str: str) -> str:
    """Resolve or create: Thunderbird / Daily Outputs / YYYY-MM-DD/

    date_str: ISO date string, e.g. '2026-06-10'
    """
    root_id = _find_or_create_folder(service, DRIVE_ROOT_FOLDER_NAME)
    parent_id = _find_or_create_folder(service, DRIVE_DAILY_PARENT, parent_id=root_id)
    daily_id = _find_or_create_folder(service, date_str, parent_id=parent_id)
    return daily_id


# ── UPLOAD ────────────────────────────────────────────────────────────────────

def _upload_file(service, local_path: Path, folder_id: str) -> Optional[str]:
    """Upload a file to Drive folder. Returns shareable link or None on failure.

    Sets link sharing so anyone with the link can view (internal use).
    """
    try:
        import mimetypes
        from googleapiclient.http import MediaFileUpload

        mime_type, _ = mimetypes.guess_type(str(local_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        file_meta = {
            "name": local_path.name,
            "parents": [folder_id],
        }

        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=False)
        uploaded = service.files().create(
            body=file_meta,
            media_body=media,
            fields="id, webViewLink",
        ).execute()

        file_id = uploaded.get("id")
        link = uploaded.get("webViewLink")

        # Make link-shareable (anyone with link can view)
        try:
            service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()
        except Exception as perm_e:
            logger.warning(f"Drive permission set failed (file still uploaded): {perm_e}")

        return link

    except Exception as e:
        logger.error(f"Drive upload failed for {local_path}: {e}")
        return None


# ── LOG I/O ───────────────────────────────────────────────────────────────────

def _load_log() -> list:
    if OUTPUT_LOG_PATH.exists():
        try:
            data = json.loads(OUTPUT_LOG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _save_log(entries: list):
    OUTPUT_LOG_PATH.write_text(
        json.dumps(entries, indent=2, default=str),
        encoding="utf-8",
    )


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def log_output(
    title: str,
    local_path: str,
    drive_folder_id: Optional[str] = None,
    date_str: Optional[str] = None,
) -> dict:
    """Log a Wing work product — upload to Drive, append to daily_output_log.json.

    Args:
        title:           Human-readable description, e.g. "McLeod T-7 departure email"
        local_path:      Absolute path to the file.
        drive_folder_id: Optional explicit Drive folder ID. If None, auto-resolves
                         Thunderbird/Daily Outputs/YYYY-MM-DD/.
        date_str:        Date key for folder (default: today MT). ISO format YYYY-MM-DD.

    Returns dict with keys: ts, title, drive_link, local_path, status
    """
    from datetime import timezone
    import zoneinfo

    mt = zoneinfo.ZoneInfo("America/Denver")
    now_mt = datetime.now(tz=mt)

    if date_str is None:
        date_str = now_mt.strftime("%Y-%m-%d")

    local = Path(local_path)
    entry: dict = {
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "title": title,
        "local_path": str(local),
        "drive_link": None,
        "drive_folder_id": None,
        "status": "pending",
        "date": date_str,
    }

    # Attempt Drive upload (fail-soft)
    try:
        if not local.exists():
            raise FileNotFoundError(f"Local file not found: {local}")

        service = _get_drive_service()

        if drive_folder_id:
            folder_id = drive_folder_id
        else:
            folder_id = _get_daily_folder_id(service, date_str)

        link = _upload_file(service, local, folder_id)

        entry["drive_link"] = link
        entry["drive_folder_id"] = folder_id
        entry["status"] = "uploaded" if link else "upload_failed"

    except Exception as e:
        logger.error(f"log_output Drive pipeline failed ({title}): {e}")
        entry["status"] = "drive_unavailable"
        entry["error"] = str(e)

    # Always append to log regardless of Drive status
    try:
        entries = _load_log()
        entries.append(entry)
        _save_log(entries)
        logger.info(
            f"Logged output: {title} | Drive: {entry.get('drive_link') or 'N/A'}"
        )
    except Exception as log_e:
        logger.error(f"Failed to write output log entry: {log_e}")

    return entry


def get_outputs_since(hours: int = 24, date_str: Optional[str] = None) -> list:
    """Return log entries from the last N hours, or matching date_str.

    Used by the brief to populate Yesterday's Outputs section.
    """
    from datetime import timezone, timedelta

    entries = _load_log()
    if not entries:
        return []

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    result = []
    for e in entries:
        try:
            ts = datetime.fromisoformat(e["ts"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                result.append(e)
        except Exception:
            # Fallback: include if date_str matches
            if date_str and e.get("date") == date_str:
                result.append(e)

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Daily Output Logger — test/authorize")
    parser.add_argument("--log", nargs=3, metavar=("TITLE", "PATH", "DATE"),
                        help="Log a file: --log 'Title' /path/to/file.txt 2026-06-10")
    parser.add_argument("--list", action="store_true", help="List last 24h entries")
    args = parser.parse_args()

    if args.log:
        title, path, date = args.log
        result = log_output(title, path, date_str=date)
        print(json.dumps(result, indent=2, default=str))
    elif args.list:
        entries = get_outputs_since(hours=24)
        print(json.dumps(entries, indent=2, default=str))
    else:
        parser.print_help()
