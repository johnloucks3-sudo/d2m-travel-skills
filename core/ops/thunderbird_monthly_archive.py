#!/usr/bin/env python3
"""
Thunderbird Monthly Archive — Product Dump to Evernote
1st of each month at 07:15 MDT

Zips all files in output/ (HTML, PDF, MD, JSON intel) and emails them
to the Evernote email-in address for permanent archive.

Usage:
    python3 thunderbird_monthly_archive.py             # Run now
    python3 thunderbird_monthly_archive.py --dry-run   # List what would be archived
    python3 thunderbird_monthly_archive.py --force     # Force re-run even if already ran this month
    python3 thunderbird_monthly_archive.py --status    # Show last run info
"""

import argparse
import json
import logging
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
OUTPUT_DIR = THUNDERBIRD_DIR / "output"
STATE_FILE = THUNDERBIRD_DIR / "monthly_archive_state.json"
LOG_FILE = THUNDERBIRD_DIR / "monthly_archive.log"

EVERNOTE_EMAIL = "yodainva.5d9fc@m.evernote.com"
MAX_ZIP_BYTES = 24 * 1024 * 1024  # 24 MB (Evernote limit is 25 MB)

INCLUDE_EXTENSIONS = {".pdf", ".html", ".md", ".json", ".xlsx", ".csv", ".txt"}
EXCLUDE_SUBDIRS = {"__pycache__", ".git", "node_modules"}

# JSON files to exclude — these are operational state, not products
EXCLUDE_JSON_PATTERNS = [
    "airline_scan_", "airline_alerts", "_state.json",
    "briefing_sent", "payment_alerts", "voice_ledger",
    "commander_inbox_log", "dani_email_log", "session_autosave",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
logger = logging.getLogger("monthly_archive")


# ─── State ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ─── File collection ─────────────────────────────────────────────────────────

def _is_excluded_json(fname: str) -> bool:
    return any(pat in fname for pat in EXCLUDE_JSON_PATTERNS)


def collect_output_files() -> list[Path]:
    """Collect all product files from output/ — PDFs, HTMLs, MDs, non-state JSONs."""
    if not OUTPUT_DIR.exists():
        return []
    result = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_SUBDIRS]
        for fname in sorted(files):
            fpath = Path(root) / fname
            if fpath.suffix.lower() not in INCLUDE_EXTENSIONS:
                continue
            if fpath.suffix.lower() == ".json" and _is_excluded_json(fname):
                continue
            result.append(fpath)
    return sorted(result)


def collect_intel_files() -> list[Path]:
    """Collect intel reports from intel/ subdirectory."""
    intel_dir = THUNDERBIRD_DIR / "intel"
    if not intel_dir.exists():
        return []
    result = []
    for fpath in sorted(intel_dir.glob("*.md")):
        result.append(fpath)
    return result


def collect_commander_review_files() -> list[Path]:
    """Collect Commander_Review docs from this month."""
    cr_dir = THUNDERBIRD_DIR / "Commander_Review"
    if not cr_dir.exists():
        return []
    now = datetime.now()
    result = []
    for fpath in sorted(cr_dir.glob("*.md")):
        try:
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
            if mtime.year == now.year and mtime.month == now.month:
                result.append(fpath)
        except Exception:
            pass
    return result


def collect_all_files() -> list[Path]:
    return sorted(set(
        collect_output_files() +
        collect_intel_files() +
        collect_commander_review_files()
    ))


# ─── Zip creation ─────────────────────────────────────────────────────────────

def create_archive_zip(files: list[Path], month_str: str) -> tuple[Path, int, int]:
    """Create zip. Returns (zip_path, zip_size, total_uncompressed)."""
    zip_name = f"thunderbird_products_{month_str}.zip"
    zip_path = THUNDERBIRD_DIR / zip_name
    total_size = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for fpath in files:
            try:
                rel = fpath.relative_to(THUNDERBIRD_DIR)
            except ValueError:
                rel = fpath.name
            try:
                zf.write(fpath, arcname=str(rel))
                total_size += fpath.stat().st_size
            except (OSError, PermissionError) as e:
                logger.warning(f"Skipping {rel}: {e}")

    zip_size = zip_path.stat().st_size
    if zip_size > MAX_ZIP_BYTES:
        # Split not supported — just warn and continue with what fits
        logger.warning(f"Archive is {zip_size / 1024 / 1024:.1f} MB — may exceed Evernote limit")

    logger.info(f"Created {zip_name}: {zip_size // 1024} KB compressed, {total_size // 1024} KB uncompressed")
    return zip_path, zip_size, total_size


# ─── Email delivery ───────────────────────────────────────────────────────────

def _send_via_gmail(zip_path: Path, subject: str, body: str) -> bool:
    """Send archive zip to Evernote email-in via Gmail API."""
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    sys.path.insert(0, str(THUNDERBIRD_DIR))
    from thunderbird_gmail import _get_gmail_service, USER_EMAIL

    service = _get_gmail_service()

    msg = MIMEMultipart()
    msg["to"] = EVERNOTE_EMAIL
    msg["from"] = USER_EMAIL
    msg["subject"] = f"{subject} @Thunderbird Backups #thunderbird #backup #products #monthly"

    msg.attach(MIMEText(body, "plain"))

    with open(zip_path, "rb") as f:
        part = MIMEBase("application", "zip")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=zip_path.name)
    msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info(f"Monthly archive emailed to Evernote: {EVERNOTE_EMAIL}")
    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_monthly_archive(force: bool = False) -> dict:
    now = datetime.now()
    month_str = now.strftime("%Y%m")
    month_display = now.strftime("%B %Y")

    state = load_state()
    last_month = state.get("last_archive", {}).get("month", "")
    if last_month == month_str and not force:
        logger.info(f"Monthly archive already ran for {month_display} — skipping")
        return {
            "status": "skipped",
            "reason": f"Already archived {month_display}",
            "last_archive": state.get("last_archive", {}),
        }

    files = collect_all_files()
    if not files:
        logger.warning("No product files found in output/ — skipping")
        return {"status": "skipped", "reason": "No files found in output/"}

    logger.info(f"Monthly archive: {len(files)} files for {month_display}")

    try:
        zip_path, zip_size, total_size = create_archive_zip(files, month_str)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    subject = f"Thunderbird Products Archive — {month_display}"
    counts = {".pdf": 0, ".html": 0, ".md": 0, ".json": 0, "other": 0}
    for f in files:
        ext = f.suffix.lower()
        if ext in counts:
            counts[ext] += 1
        else:
            counts["other"] += 1

    body = (
        f"Thunderbird Monthly Products Archive\n"
        f"Month: {month_display}\n"
        f"Generated: {now.strftime('%Y-%m-%d %H:%M MT')}\n\n"
        f"File counts:\n"
        f"  PDFs:   {counts['.pdf']}\n"
        f"  HTML:   {counts['.html']}\n"
        f"  MD:     {counts['.md']}\n"
        f"  JSON:   {counts['.json']}\n"
        f"  Other:  {counts['other']}\n"
        f"  Total:  {len(files)}\n\n"
        f"Archive size: {zip_size // 1024} KB compressed ({total_size // 1024} KB raw)\n"
        f"Attached: {zip_path.name}\n"
    )

    try:
        _send_via_gmail(zip_path, subject, body)
    except Exception as e:
        logger.error(f"Email delivery failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "zip_path": str(zip_path),
            "hint": "Zip created locally — email delivery failed",
        }

    zip_path.unlink(missing_ok=True)

    result = {
        "status": "success",
        "month": month_str,
        "month_display": month_display,
        "files_count": len(files),
        "pdf_count": counts[".pdf"],
        "html_count": counts[".html"],
        "md_count": counts[".md"],
        "zip_size_kb": zip_size // 1024,
        "total_size_kb": total_size // 1024,
        "evernote_email": EVERNOTE_EMAIL,
    }

    state["last_archive"] = result
    save_state(state)

    logger.info(f"Monthly archive complete: {len(files)} files → Evernote")
    return result


def dry_run():
    files = collect_all_files()
    total_size = sum(f.stat().st_size for f in files)
    now = datetime.now()
    print(f"\nThunderbird Monthly Archive — Dry Run")
    print(f"Month: {now.strftime('%B %Y')}")
    print(f"=" * 50)
    print(f"Files to archive: {len(files)}")
    print(f"Total size:       {total_size // 1024} KB ({total_size / 1024 / 1024:.1f} MB)")
    for ext in [".pdf", ".html", ".md", ".json"]:
        count = sum(1 for f in files if f.suffix.lower() == ext)
        if count:
            print(f"  {ext:6s}: {count}")
    print(f"\nFirst 20 files:")
    for f in files[:20]:
        try:
            rel = f.relative_to(THUNDERBIRD_DIR)
        except ValueError:
            rel = f.name
        print(f"  {str(rel)[:70]}")
    if len(files) > 20:
        print(f"  ... and {len(files) - 20} more")

    state = load_state()
    last = state.get("last_archive", {})
    print(f"\nLast archive: {last.get('month_display', 'never')}")


def show_status():
    state = load_state()
    last = state.get("last_archive", {})
    print("\nThunderbird Monthly Archive — Status")
    print("=" * 50)
    if last:
        print(f"Last archive:  {last.get('month_display', 'unknown')}")
        print(f"Status:        {last.get('status', 'unknown')}")
        print(f"Files:         {last.get('files_count', 0)}")
        print(f"Zip size:      {last.get('zip_size_kb', 0)} KB")
    else:
        print("No archive recorded yet.")


def main():
    parser = argparse.ArgumentParser(description="Thunderbird monthly product archive to Evernote")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-run even if already ran this month")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        show_status()
        return
    if args.dry_run:
        dry_run()
        return

    result = run_monthly_archive(force=args.force)
    status = result.get("status", "unknown")
    if status == "success":
        print(f"✅ Archive complete: {result['files_count']} files → Evernote ({result['month_display']})")
    elif status == "skipped":
        print(f"⏭  Skipped: {result['reason']}")
    else:
        print(f"❌ Failed: {result.get('error', 'unknown')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
