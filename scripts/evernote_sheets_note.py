"""
Evernote Sheets Mirror Summary Note
====================================

Creates a HUMAN-READABLE Evernote note summarizing the current state of the
Google Sheets mirror cached at cache/sheets_mirror/.

The note is posted to the "Thunderbird Ops" notebook via Evernote's email-in
address (the SDK is not available on this system).  It contains an HTML table
with: tab name, row count, and pull timestamp.

Auth: same Gmail token used by thunderbird_gmail.py (d2mconcierge account).
      The email is sent to the Evernote email-in address encoded with the
      target notebook in the subject line.

Usage:
    python3 scripts/evernote_sheets_note.py           # Post note now
    python3 scripts/evernote_sheets_note.py --dry-run # Print HTML, don't send

Scheduled: monthly (or on demand).
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
MIRROR_DIR = THUNDERBIRD_DIR / "cache" / "sheets_mirror"
MANIFEST_PATH = MIRROR_DIR / "manifest.json"

# Target Evernote notebook for this note (separate from the backup notebook)
OPS_NOTEBOOK = "Thunderbird Ops"

# Evernote email-in address (same account used by backup script)
EVERNOTE_EMAIL = "yodainva.5d9fc@m.evernote.com"

# ---------------------------------------------------------------------------
# Manifest loader
# ---------------------------------------------------------------------------

def load_manifest() -> dict:
    """Load and return the sheets mirror manifest. Raises if missing."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}\n"
            "Run the sheets mirror pull first."
        )
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def build_html_note(manifest: dict) -> str:
    """Build a readable HTML note from the manifest."""
    pulled_at_raw = manifest.get("pulled_at", "unknown")

    # Parse and format the pull timestamp
    try:
        pulled_dt = datetime.fromisoformat(pulled_at_raw.replace("Z", "+00:00"))
        pulled_display = pulled_dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, AttributeError):
        pulled_display = pulled_at_raw

    tabs = manifest.get("tabs", {})
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build table rows
    rows_html = ""
    for tab_name, info in tabs.items():
        file_name = info.get("file", "—")
        row_count = info.get("rows", 0)
        # All tabs share the single manifest pull timestamp
        rows_html += (
            f"<tr>"
            f"<td style='padding:6px 12px; border:1px solid #ddd;'>{tab_name}</td>"
            f"<td style='padding:6px 12px; border:1px solid #ddd; text-align:right;'>{row_count:,}</td>"
            f"<td style='padding:6px 12px; border:1px solid #ddd;'>{file_name}</td>"
            f"<td style='padding:6px 12px; border:1px solid #ddd;'>{pulled_display}</td>"
            f"</tr>\n"
        )

    total_rows = sum(info.get("rows", 0) for info in tabs.values())

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Georgia, serif; color: #222; margin: 24px; }}
    h1 {{ color: #003087; border-bottom: 2px solid #003087; padding-bottom: 6px; }}
    h2 {{ color: #444; margin-top: 24px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th {{ background: #003087; color: #fff; padding: 8px 12px; text-align: left; border: 1px solid #003087; }}
    tr:nth-child(even) {{ background: #f7f3ea; }}
    .meta {{ color: #666; font-size: 0.9em; margin-bottom: 16px; }}
    .total {{ font-weight: bold; color: #003087; }}
  </style>
</head>
<body>
  <h1>Thunderbird — Google Sheets Mirror Status</h1>
  <p class="meta">
    <b>Mirror pulled:</b> {pulled_display}<br>
    <b>Note generated:</b> {generated_at}<br>
    <b>Tabs mirrored:</b> {len(tabs)}<br>
    <b>Total rows:</b> <span class="total">{total_rows:,}</span>
  </p>

  <h2>Tab Summary</h2>
  <table>
    <thead>
      <tr>
        <th>Tab Name</th>
        <th style="text-align:right">Row Count</th>
        <th>Cache File</th>
        <th>Pull Timestamp</th>
      </tr>
    </thead>
    <tbody>
{rows_html}    </tbody>
  </table>

  <p class="meta" style="margin-top:24px;">
    Source: <code>{MIRROR_DIR}</code><br>
    Script: <code>scripts/evernote_sheets_note.py</code>
  </p>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Send via Gmail → Evernote email-in
# ---------------------------------------------------------------------------

def send_to_evernote(html: str, note_title: str) -> bool:
    """Send the HTML note to Evernote via Gmail API email-in.

    Encodes the target notebook in the email subject using Evernote's
    ``@Notebook`` syntax.  No zip attachment — the email body IS the note.

    Returns True on success, raises on failure.
    """
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    # Import Gmail service from the Wing's core email module
    sys.path.insert(0, str(THUNDERBIRD_DIR))
    from core.email.thunderbird_gmail import _get_gmail_service, USER_EMAIL

    service = _get_gmail_service()

    msg = MIMEMultipart("alternative")
    msg["to"] = EVERNOTE_EMAIL
    msg["from"] = USER_EMAIL
    # Evernote subject syntax: title @Notebook #tag
    msg["subject"] = f"{note_title} @{OPS_NOTEBOOK} #thunderbird #sheets #ops"

    # Plain-text fallback
    plain = (
        f"Thunderbird — Google Sheets Mirror Status\n"
        f"Note: {note_title}\n"
        f"Notebook: {OPS_NOTEBOOK}\n"
        f"(Open in Evernote to view the formatted table)\n"
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return True


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def run(dry_run: bool = False) -> dict:
    """Build and optionally send the Sheets state note.

    Args:
        dry_run: If True, print the HTML and return without sending.

    Returns:
        Dict with status and details.
    """
    # Load manifest
    try:
        manifest = load_manifest()
    except FileNotFoundError as e:
        return {"status": "error", "error": str(e)}

    pulled_at = manifest.get("pulled_at", "unknown")
    tab_count = len(manifest.get("tabs", {}))
    total_rows = sum(info.get("rows", 0) for info in manifest.get("tabs", {}).values())

    html = build_html_note(manifest)

    date_display = datetime.now().strftime("%Y-%m-%d")
    note_title = f"Sheets Mirror Status — {date_display}"

    if dry_run:
        print(f"\nEvernote Sheets Note — Dry Run")
        print("=" * 50)
        print(f"Note title:  {note_title}")
        print(f"Notebook:    {OPS_NOTEBOOK}")
        print(f"Pulled at:   {pulled_at}")
        print(f"Tabs:        {tab_count}")
        print(f"Total rows:  {total_rows:,}")
        print(f"\n--- HTML preview (first 1000 chars) ---")
        print(html[:1000])
        print("...\n")
        print("(Dry run — not sent)")
        return {
            "status": "dry_run",
            "note_title": note_title,
            "tab_count": tab_count,
            "total_rows": total_rows,
        }

    # Send
    try:
        send_to_evernote(html, note_title)
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "hint": "Check Gmail API token (core/email/thunderbird_gmail.py)",
        }

    result = {
        "status": "success",
        "note_title": note_title,
        "notebook": OPS_NOTEBOOK,
        "evernote_email": EVERNOTE_EMAIL,
        "tab_count": tab_count,
        "total_rows": total_rows,
        "pulled_at": pulled_at,
    }
    print(f"Sheets note sent: '{note_title}' → {OPS_NOTEBOOK} via {EVERNOTE_EMAIL}")
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Create a readable Evernote note summarizing the Sheets mirror state"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print HTML to stdout, do not send to Evernote"
    )
    args = parser.parse_args()

    result = run(dry_run=args.dry_run)
    if result.get("status") == "error":
        print(f"ERROR: {result['error']}", file=sys.stderr)
        if "hint" in result:
            print(f"Hint: {result['hint']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
