"""Thunderbird Sync — Mirror ~/Thunderbird/ to Google Drive.
Auth: service account. CLI: python3 thunderbird_sync.py [--full]"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "credentials.json"
DRIVE_TOKEN_FILE = THUNDERBIRD_DIR / "drive_token.json"
STATE_FILE = THUNDERBIRD_DIR / "thunderbird_sync_state.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]
MIRROR_FOLDER_NAME = "Thunderbird_Mirror"

INCLUDE_EXTENSIONS = {".py", ".md", ".html", ".css", ".sh", ".j2"}
INCLUDE_DIRS = {"Dossiers", "Personas", "Commander_Review"}

EXCLUDE_FILES = {"credentials.json", "gmail_token.json", "gmail_oauth_credentials.json"}
EXCLUDE_DIRS = {".venv", "venv", "__pycache__", "node_modules", ".git", "output/scheduled_reports"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("thunderbird_sync")


def _get_service():
    """Auth: OAuth (John's personal Drive) with service account fallback."""
    # Try OAuth first — uploads under John's quota
    if DRIVE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(DRIVE_TOKEN_FILE), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            DRIVE_TOKEN_FILE.write_text(creds.to_json())
        if creds and creds.valid:
            log.info("Using OAuth credentials (John's Drive)")
            return build("drive", "v3", credentials=creds)

    # Fallback to service account (limited quota)
    log.info("Using service account (limited quota — may hit storageQuotaExceeded)")
    creds = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_FILE), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def _find_or_create_folder(service, name, parent_id=None):
    """Find a folder by name (under optional parent) or create it. Returns folder ID."""
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    results = service.files().list(q=q, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = service.files().create(body=meta, fields="id").execute()
    log.info(f"Created Drive folder: {name}")
    return folder["id"]


def _ensure_drive_path(service, root_id, rel_parts):
    """Walk/create nested folders under root_id for a list of path parts. Returns leaf folder ID."""
    current = root_id
    for part in rel_parts:
        current = _find_or_create_folder(service, part, current)
    return current


def _upload_file(service, local_path, folder_id, existing_file_id=None):
    """Upload or update a file in Drive."""
    mime = "application/octet-stream"
    media = MediaFileUpload(str(local_path), mimetype=mime, resumable=False)
    if existing_file_id:
        service.files().update(fileId=existing_file_id, media_body=media).execute()
        log.info(f"  Updated: {local_path.relative_to(THUNDERBIRD_DIR)}")
    else:
        meta = {"name": local_path.name, "parents": [folder_id]}
        service.files().create(body=meta, media_body=media, fields="id").execute()
        log.info(f"  Uploaded: {local_path.relative_to(THUNDERBIRD_DIR)}")


def _find_file_in_folder(service, name, folder_id):
    """Find a file by name in a specific folder. Returns file ID or None."""
    q = f"name='{name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=q, spaces="drive", fields="files(id)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def _should_include(path: Path) -> bool:
    """Decide if a file should be synced."""
    rel = path.relative_to(THUNDERBIRD_DIR)
    parts = rel.parts

    for part in parts:
        if part in EXCLUDE_DIRS:
            return False
    rel_str = str(rel)
    for exc in EXCLUDE_DIRS:
        if rel_str.startswith(exc):
            return False
    if path.name in EXCLUDE_FILES:
        return False
    if path.suffix in (".json", ".pyc"):
        return False
    if path.suffix in INCLUDE_EXTENSIONS:
        return True
    if parts and parts[0] in INCLUDE_DIRS:
        return True
    return False


def collect_files() -> list[Path]:
    """Walk THUNDERBIRD_DIR and return list of files to sync."""
    result = []
    for root, dirs, files in os.walk(THUNDERBIRD_DIR):
        root_path = Path(root)
        # Prune excluded dirs in-place for efficiency
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            fpath = root_path / fname
            if _should_include(fpath):
                result.append(fpath)
    return sorted(result)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def sync(full: bool = False):
    log.info(f"Thunderbird Sync — {'FULL' if full else 'incremental'} — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}")

    service = _get_service()
    root_id = _find_or_create_folder(service, MIRROR_FOLDER_NAME)
    log.info(f"Mirror root: {MIRROR_FOLDER_NAME} ({root_id})")

    files = collect_files()
    log.info(f"Found {len(files)} eligible files")

    state = {} if full else load_state()
    new_state = {}
    uploaded = 0
    skipped = 0
    errors = 0

    for fpath in files:
        rel = fpath.relative_to(THUNDERBIRD_DIR)
        mtime = fpath.stat().st_mtime
        key = str(rel)

        # Incremental: skip unchanged files
        prev = state.get(key, {})
        if not full and prev.get("mtime") == mtime:
            new_state[key] = prev
            skipped += 1
            continue

        # Ensure parent folders exist on Drive
        parent_parts = list(rel.parent.parts)
        folder_id = _ensure_drive_path(service, root_id, parent_parts) if parent_parts else root_id

        # Check if file already exists in that folder (for update vs create)
        existing_id = prev.get("drive_id")
        if not existing_id:
            existing_id = _find_file_in_folder(service, fpath.name, folder_id)

        try:
            _upload_file(service, fpath, folder_id, existing_id)
            uploaded += 1

            # Get the drive file ID for state tracking
            if not existing_id:
                existing_id = _find_file_in_folder(service, fpath.name, folder_id)
            new_state[key] = {"mtime": mtime, "drive_id": existing_id}

            # Save state every 25 files to avoid losing progress
            if uploaded % 25 == 0:
                save_state(new_state)
                log.info(f"  Checkpoint: {uploaded} uploaded so far")

        except Exception as e:
            errors += 1
            log.warning(f"  SKIP (error): {rel} — {e}")
            # Carry forward old state if available
            if prev:
                new_state[key] = prev

    save_state(new_state)
    log.info(f"Done — {uploaded} uploaded, {skipped} skipped, {errors} errors")


def main():
    parser = argparse.ArgumentParser(description="Mirror ~/Thunderbird/ to Google Drive")
    parser.add_argument("--full", action="store_true", help="Full resync (ignore state file)")
    args = parser.parse_args()
    try:
        sync(full=args.full)
    except Exception as e:
        log.error(f"Sync failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
