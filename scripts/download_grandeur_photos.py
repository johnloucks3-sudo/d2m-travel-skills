#!/usr/bin/env python3
"""
Download Grandeur ship photos from Google Drive folder.
Uses direct googleapiclient OAuth.

Usage:
  python3 scripts/download_grandeur_photos.py [--output-dir /path]
"""

import sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TOKEN_FILE = Path.home() / "Thunderbird" / "drive_token.json"
GRANDEUR_FOLDER_ID = "1e-0rbVOhvI-jB4WPwBf1DBu591s0uXJ1"

def get_drive_service():
    token_file = TOKEN_FILE.expanduser().resolve()
    if not token_file.exists():
        print(f"FATAL: Drive token not found at {token_file}")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired:
        print("Token expired — refreshing...")
        creds.refresh(Request())
        token_file.write_text(creds.to_json())

    return build("drive", "v3", credentials=creds)

def list_folder_files(service, folder_id):
    """List all files in a Drive folder."""
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name, mimeType)",
        pageSize=100
    ).execute()
    return results.get("files", [])

def download_file(service, file_id, file_name, output_dir):
    """Download a file from Drive to local path."""
    output_path = output_dir / file_name

    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(str(output_path), mode='wb')
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"  Downloaded {int(status.progress() * 100)}%...", end='\r')

    fh.close()
    print(f"✓ {file_name}")
    return output_path

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=Path.home() / 'Thunderbird' / 'output' / 'Grandeur_Scandinavia_Portal' / 'assets')
    args = parser.parse_args()

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Grandeur photos to: {output_dir}")

    service = get_drive_service()

    # List files in folder
    files = list_folder_files(service, GRANDEUR_FOLDER_ID)

    if not files:
        print("No files found in folder")
        return

    print(f"Found {len(files)} files in Grandeur folder:")

    downloaded = []
    for file_info in files:
        # Skip PDFs and manifest for now, focus on images
        file_name = file_info['name']
        file_id = file_info['id']
        mime_type = file_info.get('mimeType', '')

        # Only download images and GIFs
        if any(x in mime_type.lower() for x in ['image', 'gif']) or file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            print(f"Downloading: {file_name}")
            try:
                download_file(service, file_id, file_name, output_dir)
                downloaded.append(file_name)
            except Exception as e:
                print(f"✗ Failed to download {file_name}: {e}")

    print(f"\nDownloaded {len(downloaded)} image files")
    for fn in downloaded:
        print(f"  - {fn}")

if __name__ == '__main__':
    main()
