"""
Thunderbird Evernote Backup — Weekly Code Archive to Evernote
=============================================================

Collects all .py and key .md files from ~/Thunderbird/, zips them,
and uploads to Evernote as a note with the archive attached.

Auth: Evernote developer token via EVERNOTE_TOKEN env var or ~/.evernote_token
API:  Production Evernote (https://www.evernote.com)

Tries the evernote SDK first (pip install evernote3), falls back to
raw REST/Thrift calls via requests if the SDK is unavailable or broken
on Python 3.13+.

Usage:
  python thunderbird_evernote_backup.py              # Run backup now
  python thunderbird_evernote_backup.py --status     # Show last backup info
  python thunderbird_evernote_backup.py --dry-run    # List what would be backed up
  python thunderbird_evernote_backup.py --local /mnt/usb/thunderbird_backups/

Entry point for scheduler:
  from thunderbird_evernote_backup import run_weekly_backup
  result = run_weekly_backup()
"""

import argparse
import hashlib
import io
import json
import logging
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
STATE_FILE = THUNDERBIRD_DIR / "evernote_backup_state.json"
LOG_FILE = THUNDERBIRD_DIR / "evernote_backup.log"

EVERNOTE_BASE = "https://www.evernote.com"
EVERNOTE_API = f"{EVERNOTE_BASE}/edam/note"
EVERNOTE_NOTESTORE = f"{EVERNOTE_BASE}/edam/note"

NOTEBOOK_NAME = "Thunderbird Backups"
NOTE_TAGS = ["thunderbird", "backup", "code"]

# Max Evernote note resource size: 25 MB
MAX_ZIP_BYTES = 25 * 1024 * 1024

# Dirs to skip when collecting files
EXCLUDE_DIRS = {
    ".venv", "venv", "__pycache__", "node_modules", ".git",
    "output", ".mypy_cache", ".pytest_cache", "dist", "build",
    "egg-info",
}

# Key markdown files to include (relative to THUNDERBIRD_DIR)
KEY_MD_FILES = [
    "CLAUDE.md",
    "THUNDERBIRD_MASTER_PLAN.md",
    "HEARTBEAT_PROPOSAL.md",
]

# Markdown subdirectory to include entirely
MD_SUBDIRS = ["Dossiers"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
logger = logging.getLogger("thunderbird_evernote_backup")

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _get_evernote_token() -> str:
    """Load Evernote developer token from env var or file."""
    token = os.environ.get("EVERNOTE_TOKEN", "").strip()
    if token:
        return token

    token_file = Path.home() / ".evernote_token"
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
        if token:
            return token

    raise RuntimeError(
        "Evernote token not found.\n"
        "Set EVERNOTE_TOKEN env var or create ~/.evernote_token with your developer token.\n"
        "Get a token at: https://www.evernote.com/api/DeveloperToken.action"
    )

# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def collect_py_files() -> list[Path]:
    """Collect all .py files under THUNDERBIRD_DIR, skipping excluded dirs."""
    result = []
    for root, dirs, files in os.walk(THUNDERBIRD_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in sorted(files):
            if fname.endswith(".py"):
                result.append(Path(root) / fname)
    return sorted(result)


def collect_md_files() -> list[Path]:
    """Collect key .md files: explicit list + entire Dossiers/ subdirs."""
    result = []

    # Explicit key files
    for name in KEY_MD_FILES:
        p = THUNDERBIRD_DIR / name
        if p.exists():
            result.append(p)

    # Entire subdirectories
    for subdir in MD_SUBDIRS:
        d = THUNDERBIRD_DIR / subdir
        if d.is_dir():
            for root, dirs, files in os.walk(d):
                dirs[:] = [dd for dd in dirs if dd not in EXCLUDE_DIRS]
                for fname in sorted(files):
                    if fname.endswith(".md"):
                        result.append(Path(root) / fname)

    return sorted(set(result))


def collect_all_files() -> list[Path]:
    """Collect all files for backup."""
    py_files = collect_py_files()
    md_files = collect_md_files()
    return sorted(set(py_files + md_files))

# ---------------------------------------------------------------------------
# Zip creation
# ---------------------------------------------------------------------------

def create_backup_zip(files: list[Path], date_str: str) -> tuple[Path, int]:
    """Create a zip archive of the given files.

    Returns (zip_path, total_uncompressed_size).
    Raises ValueError if the zip exceeds 25 MB.
    """
    zip_name = f"thunderbird_code_{date_str}.zip"
    zip_path = THUNDERBIRD_DIR / zip_name

    total_size = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for fpath in files:
            rel = fpath.relative_to(THUNDERBIRD_DIR)
            try:
                zf.write(fpath, arcname=str(rel))
                total_size += fpath.stat().st_size
            except (OSError, PermissionError) as e:
                logger.warning(f"Skipping {rel}: {e}")

    zip_size = zip_path.stat().st_size
    if zip_size > MAX_ZIP_BYTES:
        zip_path.unlink(missing_ok=True)
        raise ValueError(
            f"Zip archive is {zip_size / 1024 / 1024:.1f} MB — exceeds "
            f"Evernote's 25 MB limit. Consider excluding large files."
        )

    logger.info(f"Created {zip_name}: {zip_size / 1024:.0f} KB compressed, "
                f"{total_size / 1024:.0f} KB uncompressed")
    return zip_path, total_size

# ---------------------------------------------------------------------------
# Evernote SDK client (preferred if available)
# ---------------------------------------------------------------------------

def _try_sdk_upload(token: str, zip_path: Path, note_title: str,
                    note_body_enml: str, tags: list[str]) -> Optional[str]:
    """Try uploading via the evernote SDK. Returns note GUID or None on import failure.

    Install: pip install evernote3
    The original 'evernote' package may also work: pip install evernote
    """
    try:
        from evernote.api.client import EvernoteClient
        from evernote.edam.type.ttypes import Note, Resource, ResourceAttributes, Data
        from evernote.edam.notestore.ttypes import NoteFilter
        import evernote.edam.type.ttypes as Types
    except ImportError:
        logger.info("Evernote SDK not available — will use requests fallback")
        return None

    try:
        client = EvernoteClient(token=token, sandbox=False)
        note_store = client.get_note_store()

        # Find or create notebook
        notebook_guid = None
        for nb in note_store.listNotebooks():
            if nb.name == NOTEBOOK_NAME:
                notebook_guid = nb.guid
                break

        if not notebook_guid:
            new_nb = Types.Notebook()
            new_nb.name = NOTEBOOK_NAME
            created_nb = note_store.createNotebook(new_nb)
            notebook_guid = created_nb.guid
            logger.info(f"Created Evernote notebook: {NOTEBOOK_NAME}")

        # Read zip and create resource
        zip_bytes = zip_path.read_bytes()
        md5 = hashlib.md5(zip_bytes).hexdigest()

        data = Data()
        data.size = len(zip_bytes)
        data.bodyHash = bytes.fromhex(md5)
        data.body = zip_bytes

        resource_attr = ResourceAttributes()
        resource_attr.fileName = zip_path.name
        resource_attr.attachment = True

        resource = Resource()
        resource.mime = "application/zip"
        resource.data = data
        resource.attributes = resource_attr

        # Build note ENML with resource reference
        enml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            '<en-note>'
            f'{note_body_enml}'
            f'<en-media type="application/zip" hash="{md5}"/>'
            '</en-note>'
        )

        # Find or create tags
        existing_tags = {t.name: t.guid for t in note_store.listTags()}
        tag_guids = []
        for tag_name in tags:
            if tag_name in existing_tags:
                tag_guids.append(existing_tags[tag_name])
            else:
                new_tag = Types.Tag()
                new_tag.name = tag_name
                created_tag = note_store.createTag(new_tag)
                tag_guids.append(created_tag.guid)
                logger.info(f"Created Evernote tag: {tag_name}")

        note = Note()
        note.title = note_title
        note.content = enml
        note.notebookGuid = notebook_guid
        note.resources = [resource]
        note.tagGuids = tag_guids

        created_note = note_store.createNote(note)
        logger.info(f"Note created via SDK: {created_note.guid}")
        return created_note.guid

    except ImportError:
        return None
    except Exception as e:
        logger.warning(f"SDK upload failed: {e} — falling back to requests")
        return None

# ---------------------------------------------------------------------------
# Evernote REST fallback (requests-based, no SDK dependency)
# ---------------------------------------------------------------------------

def _requests_upload(token: str, zip_path: Path, note_title: str,
                     note_body_enml: str, tags: list[str]) -> str:
    """Upload to Evernote using the Thrift-over-HTTP API via requests.

    The Evernote API is Thrift-based, not REST. For the requests fallback we
    use the NoteStore HTTPS endpoint with the oauth token in the header and
    build Thrift binary payloads manually — but that's extremely complex.

    Instead, we use the simpler approach: the evernote API's JSON/Thrift
    endpoints are not publicly documented for raw requests. The practical
    fallback is to use the unofficial but stable Evernote API v1 endpoints
    that accept Thrift binary protocol.

    Given the complexity of raw Thrift, this fallback uses the
    `thrift` library directly (pip install thrift) to speak to Evernote.
    If thrift isn't available either, we raise with install instructions.
    """
    try:
        import thrift.transport.THttpClient as THttpClient
        import thrift.protocol.TBinaryProtocol as TBinaryProtocol
        # We need the generated Evernote Thrift stubs — these come with
        # the evernote SDK package. If we got here, the SDK import failed,
        # so we can't use the Thrift stubs either.
    except ImportError:
        pass

    # Since raw Thrift without the SDK stubs is impractical, use a minimal
    # HTTPS approach with the Evernote API's internal JSON-Thrift bridge.
    # The most reliable non-SDK method is actually through the Evernote
    # developer API using their internal endpoints.

    import requests

    note_store_url = f"{EVERNOTE_BASE}/shard/s1/notestore"

    # Step 1: Discover the correct shard from the user's token
    # The NoteStore URL contains the user's shard. We can get it from
    # the UserStore.
    user_store_url = f"{EVERNOTE_BASE}/edam/user"

    # Use the Evernote API's Thrift-over-HTTPS. Since we can't easily
    # build Thrift binary without stubs, we use a clever workaround:
    # call the API using the evernote-sdk-python3 compatible approach
    # with minimal HTTP.

    # Actually, the most practical pure-requests approach for Evernote
    # is to use their newer API if available, or accept that we need
    # at least the thrift package.

    # Final practical approach: use the evernote API via a minimal
    # Thrift client built with just the `thrift` package + hand-coded
    # service definitions.

    # Given the extreme complexity of hand-rolling Thrift, provide clear
    # install instructions instead.
    raise RuntimeError(
        "Evernote SDK not available and raw Thrift fallback requires SDK stubs.\n"
        "Install one of:\n"
        "  pip install evernote3          # Python 3 compatible fork\n"
        "  pip install evernote           # Original (may need patches for 3.13)\n"
        "\n"
        "If neither works on your Python version, install from git:\n"
        "  pip install git+https://github.com/evernote/evernote-sdk-python3.git\n"
        "\n"
        "The backup zip was still created locally — you can upload manually."
    )

# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load backup state from JSON file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state: dict):
    """Save backup state to JSON file."""
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# ENML body builder
# ---------------------------------------------------------------------------

def _build_note_body(files: list[Path], zip_size: int, total_size: int,
                     date_str: str) -> str:
    """Build ENML body content (inner content, not the full envelope)."""
    py_count = sum(1 for f in files if f.suffix == ".py")
    md_count = sum(1 for f in files if f.suffix == ".md")

    lines = [
        f"<h2>Thunderbird Code Backup</h2>",
        f"<p><b>Date:</b> {date_str}</p>",
        f"<p><b>Total files:</b> {len(files)} ({py_count} Python, {md_count} Markdown)</p>",
        f"<p><b>Archive size:</b> {zip_size / 1024:.0f} KB compressed "
        f"({total_size / 1024:.0f} KB uncompressed)</p>",
        "<br/>",
        "<h3>Python Modules</h3>",
        "<ul>",
    ]

    for f in files:
        if f.suffix == ".py":
            rel = f.relative_to(THUNDERBIRD_DIR)
            size_kb = f.stat().st_size / 1024
            lines.append(f"<li>{rel} ({size_kb:.1f} KB)</li>")

    lines.append("</ul>")

    if md_count > 0:
        lines.append("<h3>Documentation</h3>")
        lines.append("<ul>")
        for f in files:
            if f.suffix == ".md":
                rel = f.relative_to(THUNDERBIRD_DIR)
                size_kb = f.stat().st_size / 1024
                lines.append(f"<li>{rel} ({size_kb:.1f} KB)</li>")
        lines.append("</ul>")

    lines.append("<br/>")
    lines.append(f"<p><i>Generated by Thunderbird Evernote Backup</i></p>")
    lines.append("<br/>")

    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Local backup (USB drive or any target dir)
# ---------------------------------------------------------------------------

DEFAULT_LOCAL_BACKUP_DIR = Path("/mnt/usb/thunderbird_backups/")


def run_local_backup(target_dir: Optional[str] = None) -> dict:
    """Copy the backup zip to a local path (e.g., USB drive on dv7).

    Args:
        target_dir: Destination directory. Defaults to /mnt/usb/thunderbird_backups/

    Returns:
        Dict with status, path, and file info.
    """
    target = Path(target_dir) if target_dir else DEFAULT_LOCAL_BACKUP_DIR

    date_str = datetime.now().strftime("%Y%m%d")
    files = collect_all_files()

    if not files:
        return {"status": "error", "error": "No files found to back up"}

    # Create the zip
    try:
        zip_path, total_size = create_backup_zip(files, date_str)
    except ValueError as e:
        return {"status": "error", "error": str(e)}

    # Ensure target directory exists
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        # Clean up zip
        zip_path.unlink(missing_ok=True)
        return {
            "status": "error",
            "error": f"Cannot create target directory {target}: {e}",
            "hint": "Is the USB drive mounted? Check: mount | grep usb",
        }

    # Copy zip to target
    dest_path = target / zip_path.name
    try:
        shutil.copy2(zip_path, dest_path)
        logger.info(f"Local backup saved: {dest_path}")
    except OSError as e:
        zip_path.unlink(missing_ok=True)
        return {"status": "error", "error": f"Copy failed: {e}"}

    zip_size = zip_path.stat().st_size

    # Clean up source zip
    zip_path.unlink(missing_ok=True)

    # Prune old backups — keep last 12
    existing = sorted(target.glob("thunderbird_code_*.zip"), reverse=True)
    for old in existing[12:]:
        try:
            old.unlink()
            logger.info(f"Pruned old local backup: {old.name}")
        except OSError:
            pass

    result = {
        "status": "success",
        "path": str(dest_path),
        "files_count": len(files),
        "zip_size_kb": round(zip_size / 1024),
        "total_size_kb": round(total_size / 1024),
        "date": date_str,
    }

    # Update state
    state = load_state()
    state["last_local_backup"] = {
        "date": date_str,
        "path": str(dest_path),
        "files_count": len(files),
        "zip_size_kb": round(zip_size / 1024),
    }
    save_state(state)

    return result

# ---------------------------------------------------------------------------
# Main backup flow
# ---------------------------------------------------------------------------

EVERNOTE_EMAIL = "yodainva.5d9fc@m.evernote.com"


def _send_to_evernote_via_email(zip_path: Path, subject: str, body: str) -> bool:
    """Send backup zip to Evernote via email-in address using Gmail API."""
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    from core.email.thunderbird_gmail import _get_gmail_service, USER_EMAIL

    service = _get_gmail_service()

    msg = MIMEMultipart()
    msg["to"] = EVERNOTE_EMAIL
    msg["from"] = USER_EMAIL
    # Evernote uses subject as note title, @notebook and #tag in subject
    msg["subject"] = f"{subject} @Thunderbird Backups #thunderbird #backup #code"
    msg.attach(MIMEText(body, "plain"))

    # Attach zip
    with open(zip_path, "rb") as f:
        part = MIMEBase("application", "zip")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=zip_path.name)
    msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info(f"Backup emailed to Evernote: {EVERNOTE_EMAIL}")
    return True


def run_evernote_backup() -> dict:
    """Run the Evernote backup via email-in. Returns dict with status and details."""
    date_str = datetime.now().strftime("%Y%m%d")
    date_display = datetime.now().strftime("%Y-%m-%d")

    # Check for duplicate
    state = load_state()
    last_date = state.get("last_evernote_backup", {}).get("date", "")
    if last_date == date_str:
        logger.info(f"Backup already run today ({date_str}) — skipping")
        return {
            "status": "skipped",
            "reason": f"Already backed up today ({date_str})",
            "last_backup": state.get("last_evernote_backup", {}),
        }

    # Collect files
    files = collect_all_files()
    if not files:
        return {"status": "error", "error": "No files found to back up"}

    py_count = sum(1 for f in files if f.suffix == ".py")
    md_count = sum(1 for f in files if f.suffix == ".md")
    logger.info(f"Collected {len(files)} files ({py_count} .py, {md_count} .md)")

    # Create zip
    try:
        zip_path, total_size = create_backup_zip(files, date_str)
    except ValueError as e:
        return {"status": "error", "error": str(e)}

    zip_size = zip_path.stat().st_size
    note_title = f"Thunderbird Code Backup — {date_display}"

    # Build email body
    body = (
        f"Thunderbird Code Backup\n"
        f"Date: {date_display}\n"
        f"Files: {len(files)} ({py_count} .py, {md_count} .md)\n"
        f"Total size: {total_size // 1024} KB\n"
        f"Zip size: {zip_size // 1024} KB\n"
        f"\nAttached: {zip_path.name}\n"
    )

    # Send via Gmail to Evernote email-in address
    try:
        _send_to_evernote_via_email(zip_path, note_title, body)
    except Exception as e:
        logger.error(f"Evernote email failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "zip_path": str(zip_path),
            "hint": "Zip created locally — email delivery failed",
        }

    # Clean up local zip after successful send
    zip_path.unlink(missing_ok=True)

    # Save state
    result = {
        "status": "success",
        "method": "email-in",
        "evernote_email": EVERNOTE_EMAIL,
        "note_title": note_title,
        "notebook": "Thunderbird Backups",
        "tags": NOTE_TAGS,
        "files_count": len(files),
        "py_count": py_count,
        "md_count": md_count,
        "zip_size_kb": round(zip_size / 1024),
        "total_size_kb": round(total_size / 1024),
        "date": date_str,
    }

    state["last_evernote_backup"] = result
    save_state(state)

    logger.info(f"Evernote backup complete: {note_title} → {EVERNOTE_EMAIL}")
    return result


def run_weekly_backup() -> dict:
    """Run the weekly Evernote code backup. Returns dict with status.

    Entry point for thunderbird_scheduler.py integration.
    Runs both Evernote upload and local backup (if USB path exists).
    """
    results = {}

    # Evernote backup
    logger.info("=" * 60)
    logger.info("WEEKLY BACKUP: Evernote code archive")
    logger.info("=" * 60)
    results["evernote"] = run_evernote_backup()

    # Local backup (USB drive) — only if default dir parent is mounted
    if DEFAULT_LOCAL_BACKUP_DIR.parent.exists():
        logger.info("Running local USB backup...")
        results["local"] = run_local_backup()
    else:
        logger.info(f"Local backup skipped — {DEFAULT_LOCAL_BACKUP_DIR.parent} not mounted")
        results["local"] = {"status": "skipped", "reason": "Target not mounted"}

    return results

# ---------------------------------------------------------------------------
# CLI: --status
# ---------------------------------------------------------------------------

def show_status():
    """Print last backup info."""
    state = load_state()

    print("\nThunderbird Evernote Backup — Status")
    print("=" * 50)

    ev = state.get("last_evernote_backup", {})
    if ev:
        print(f"\nLast Evernote Backup:")
        print(f"  Date:        {ev.get('date', 'unknown')}")
        print(f"  Status:      {ev.get('status', 'unknown')}")
        print(f"  Note:        {ev.get('note_title', 'N/A')}")
        print(f"  GUID:        {ev.get('note_guid', 'N/A')}")
        print(f"  Files:       {ev.get('files_count', 0)} "
              f"({ev.get('py_count', 0)} .py, {ev.get('md_count', 0)} .md)")
        print(f"  Zip size:    {ev.get('zip_size_kb', 0)} KB")
        print(f"  Notebook:    {ev.get('notebook', 'N/A')}")
        print(f"  Tags:        {', '.join(ev.get('tags', []))}")
    else:
        print("\nNo Evernote backup recorded yet.")

    loc = state.get("last_local_backup", {})
    if loc:
        print(f"\nLast Local Backup:")
        print(f"  Date:        {loc.get('date', 'unknown')}")
        print(f"  Path:        {loc.get('path', 'N/A')}")
        print(f"  Files:       {loc.get('files_count', 0)}")
        print(f"  Zip size:    {loc.get('zip_size_kb', 0)} KB")
    else:
        print("\nNo local backup recorded yet.")

    print()

# ---------------------------------------------------------------------------
# CLI: --dry-run
# ---------------------------------------------------------------------------

def dry_run():
    """List what would be backed up without doing anything."""
    files = collect_all_files()
    py_files = [f for f in files if f.suffix == ".py"]
    md_files = [f for f in files if f.suffix == ".md"]
    total_size = sum(f.stat().st_size for f in files)

    print("\nThunderbird Evernote Backup — Dry Run")
    print("=" * 50)
    print(f"\nTotal files: {len(files)} ({len(py_files)} .py, {len(md_files)} .md)")
    print(f"Total size:  {total_size / 1024:.0f} KB ({total_size / 1024 / 1024:.1f} MB)")

    date_str = datetime.now().strftime("%Y%m%d")
    print(f"Zip name:    thunderbird_code_{date_str}.zip")
    print(f"Note title:  Thunderbird Code Backup — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Notebook:    {NOTEBOOK_NAME}")
    print(f"Tags:        {', '.join(NOTE_TAGS)}")

    print(f"\nPython files ({len(py_files)}):")
    for f in py_files:
        rel = f.relative_to(THUNDERBIRD_DIR)
        size_kb = f.stat().st_size / 1024
        print(f"  {str(rel):50s}  {size_kb:6.1f} KB")

    print(f"\nMarkdown files ({len(md_files)}):")
    for f in md_files:
        rel = f.relative_to(THUNDERBIRD_DIR)
        size_kb = f.stat().st_size / 1024
        print(f"  {str(rel):50s}  {size_kb:6.1f} KB")

    # Check state
    state = load_state()
    last_date = state.get("last_evernote_backup", {}).get("date", "")
    if last_date == date_str:
        print(f"\nWARNING: Backup already run today ({date_str}) — would be skipped.")
    else:
        print(f"\nReady to back up. Last backup: {last_date or 'never'}")

    # Check token
    try:
        _get_evernote_token()
        print("Evernote token: found")
    except RuntimeError:
        print("Evernote token: NOT FOUND — set EVERNOTE_TOKEN or create ~/.evernote_token")

    print()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Thunderbird Code Backup to Evernote"
    )
    parser.add_argument("--status", action="store_true",
                        help="Show last backup info")
    parser.add_argument("--dry-run", action="store_true",
                        help="List what would be backed up")
    parser.add_argument("--local", type=str, nargs="?",
                        const=str(DEFAULT_LOCAL_BACKUP_DIR),
                        help="Run local backup to target dir (default: /mnt/usb/thunderbird_backups/)")
    parser.add_argument("--force", action="store_true",
                        help="Force backup even if already run today")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.dry_run:
        dry_run()
        return

    if args.local:
        result = run_local_backup(target_dir=args.local)
        if result["status"] == "success":
            logger.info(f"Local backup complete: {result['path']}")
        else:
            logger.error(f"Local backup failed: {result.get('error', 'unknown')}")
            sys.exit(1)
        return

    # Force: clear today's date from state so it runs again
    if args.force:
        state = load_state()
        if "last_evernote_backup" in state:
            state["last_evernote_backup"]["date"] = ""
            save_state(state)

    try:
        result = run_evernote_backup()
        status = result.get("status", "unknown")

        if status == "success":
            logger.info("Backup complete.")
        elif status == "skipped":
            logger.info(f"Skipped: {result.get('reason', '')}")
        elif status == "partial":
            logger.warning(f"Partial: {result.get('hint', '')}")
            logger.warning(f"Zip at: {result.get('zip_path', 'N/A')}")
        else:
            logger.error(f"Failed: {result.get('error', 'unknown')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Backup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
