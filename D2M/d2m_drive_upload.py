#!/usr/bin/env python3
"""
d2m_drive_upload.py
Dreams2Memories Travel — Thunderbird Wing
Upload any file to Google Drive via n8n webhook.

Usage:
  python3 d2m_drive_upload.py <file_path> [--folder-id <id>] [--description <text>]

Examples:
  python3 d2m_drive_upload.py ~/docs/Kuklinski_Lifecycle_Email_Library.md
  python3 d2m_drive_upload.py ~/docs/report.md --folder-id 1aVU22PPvcKMUFtyRDDpAYhqCvWTBohR7
  python3 d2m_drive_upload.py ~/docs/report.pdf --description "Monthly report Apr 2026"
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

# ── Configuration ──────────────────────────────────────────────────────────────

N8N_WEBHOOK_URL = "https://n8n.d2mluxury.quest/webhook/drive-upload"

# Default folder IDs (Google Drive)
FOLDER_IDS = {
    "kuklinski":  "1aVU22PPvcKMUFtyRDDpAYhqCvWTBohR7",
    "d2m_root":   "1MjjbqQVnzMYpHyAtNu-zZej-1mXhHkGk",   # D2M root from Thunderbird config
    "default":    "1MjjbqQVnzMYpHyAtNu-zZej-1mXhHkGk",
}

# MIME type map
MIME_TYPES = {
    ".md":   "text/markdown",
    ".txt":  "text/plain",
    ".html": "text/html",
    ".json": "application/json",
    ".csv":  "text/csv",
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

# ── Core Upload Function ────────────────────────────────────────────────────────

def upload_file(
    file_path: str,
    folder_id: str = None,
    folder_name: str = "default",
    description: str = None,
    dry_run: bool = False,
) -> dict:
    """
    Upload a file to Google Drive via n8n webhook.
    Returns the JSON response from n8n on success.
    """
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Resolve folder ID
    resolved_folder = folder_id or FOLDER_IDS.get(folder_name) or FOLDER_IDS["default"]

    # Determine MIME type
    ext = path.suffix.lower()
    mime_type = MIME_TYPES.get(ext, "application/octet-stream")

    # Read file content
    if mime_type.startswith("text/") or mime_type == "application/json":
        content = path.read_text(encoding="utf-8")
    else:
        # Binary files: base64 encode
        import base64
        content = base64.b64encode(path.read_bytes()).decode("utf-8")
        mime_type = f"base64:{mime_type}"  # Signal to n8n it's base64

    filename = path.name
    desc = description or f"Uploaded by Thunderbird Wing — {path.name}"

    payload = {
        "filename":    filename,
        "content":     content,
        "folder_id":   resolved_folder,
        "mime_type":   mime_type,
        "description": desc,
    }

    print(f"\n📤 D2M Drive Upload")
    print(f"   File     : {filename}")
    print(f"   Size     : {len(content):,} chars")
    print(f"   MIME     : {mime_type}")
    print(f"   Folder ID: {resolved_folder}")
    print(f"   Webhook  : {N8N_WEBHOOK_URL}")

    if dry_run:
        print("\n⚡ DRY RUN — payload validated, no upload performed.")
        return {"status": "dry_run", "payload_size": len(json.dumps(payload))}

    print("\n   Sending to n8n...")

    response = requests.post(
        N8N_WEBHOOK_URL,
        json=payload,
        timeout=30,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Upload successful!")
        print(f"   Drive URL : {result.get('drive_url', 'N/A')}")
        print(f"   File ID   : {result.get('file_id', 'N/A')}")
        print(f"   Uploaded  : {result.get('uploaded_at', 'N/A')}")
        return result
    else:
        print(f"\n❌ Upload failed — HTTP {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        response.raise_for_status()


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Upload a file to Google Drive via D2M n8n webhook",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Folder shortcuts:
  kuklinski  → Kuklinski client folder
  d2m_root   → D2M Drive root
  default    → D2M Drive root (fallback)

Or pass a raw Google Drive folder ID with --folder-id.
        """,
    )
    parser.add_argument("file", help="Path to file to upload")
    parser.add_argument("--folder-id", help="Google Drive folder ID (overrides --folder-name)")
    parser.add_argument(
        "--folder-name",
        choices=list(FOLDER_IDS.keys()),
        default="default",
        help="Named folder shortcut (default: 'default')",
    )
    parser.add_argument("--description", help="File description in Drive")
    parser.add_argument("--dry-run", action="store_true", help="Validate payload without uploading")

    args = parser.parse_args()

    try:
        result = upload_file(
            file_path=args.file,
            folder_id=args.folder_id,
            folder_name=args.folder_name,
            description=args.description,
            dry_run=args.dry_run,
        )
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"\n❌ Network error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
