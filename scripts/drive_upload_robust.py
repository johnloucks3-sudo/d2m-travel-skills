#!/usr/bin/env python3
"""
drive_upload_robust.py — Standalone Google Drive uploader.
Bypasses n8n entirely. Uses direct googleapiclient OAuth.
Dreams2Memories Travel, LLC · Thunderbird Wing

Usage:
  python3 scripts/drive_upload_robust.py <file_path> [--folder-id <id>] [--name <name>]

Examples:
  python3 scripts/drive_upload_robust.py ~/report.pdf
  python3 scripts/drive_upload_robust.py ~/report.pdf --folder-id 1aVU22PPvcKMUFtyRDDpAYhqCvWTBohR7
  python3 scripts/drive_upload_robust.py ~/report.pdf --name "Q2 Report.pdf"
"""

import argparse
import mimetypes
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_FILE = Path.home() / "Thunderbird" / "drive_token.json"


def get_drive_service():
    token_file = TOKEN_FILE.expanduser().resolve()
    if not token_file.exists():
        print(f"FATAL: Drive token not found at {token_file}")
        print("Run: python3 api/thunderbird_google_auth.py --authorize-persona")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired:
        print("Token expired — refreshing...")
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
        print("Token refreshed and saved.")
    elif not creds.valid:
        print(f"FATAL: Token invalid at {token_file}")
        sys.exit(1)

    return build("drive", "v3", credentials=creds)


def upload_file(local_path, folder_id=None, name=None):
    path = Path(local_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    file_name = name or path.name
    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    file_size = path.stat().st_size

    service = get_drive_service()
    metadata = {"name": file_name}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaFileUpload(str(path), mimetype=mime_type, resumable=True)

    print(f"Uploading {file_name} ({file_size:,} bytes, {mime_type})...")
    uploaded = (
        service.files()
        .create(body=metadata, media_body=media, fields="id, name, webViewLink, size")
        .execute()
    )

    print(f"  File ID:  {uploaded['id']}")
    print(f"  Name:     {uploaded['name']}")
    print(f"  View:     {uploaded['webViewLink']}")
    return uploaded


def main():
    parser = argparse.ArgumentParser(
        description="Upload a file to Google Drive directly (no n8n)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="Path to file to upload")
    parser.add_argument("--folder-id", help="Google Drive folder ID (omit for root)")
    parser.add_argument("--name", help="File name in Drive (defaults to local filename)")

    args = parser.parse_args()

    try:
        upload_file(args.file, args.folder_id, args.name)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
