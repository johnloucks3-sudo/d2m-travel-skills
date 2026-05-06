"""Helpers for commission audit — Drive/Sheets/PDF extraction."""
import io
import json
import re
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


def get_services():
    creds_path = Path("creds/drive_token.json")
    creds = Credentials.from_authorized_user_info(json.loads(creds_path.read_text()))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        creds_path.write_text(creds.to_json())
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)
    return drive, sheets


def list_folder(drive, folder_id, page_size=500):
    """List all files in a Drive folder (recursive=False)."""
    items = []
    page_token = None
    while True:
        resp = drive.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)",
            pageSize=page_size,
            pageToken=page_token,
        ).execute()
        items.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def list_folder_recursive(drive, folder_id, max_depth=3, _depth=0):
    """Recursively list files; returns list of (file, path)."""
    out = []
    items = list_folder(drive, folder_id)
    for it in items:
        if it["mimeType"] == "application/vnd.google-apps.folder" and _depth < max_depth:
            sub = list_folder_recursive(drive, it["id"], max_depth, _depth + 1)
            for sf, sp in sub:
                out.append((sf, [it["name"]] + sp))
        else:
            out.append((it, []))
    return out


def download_pdf(drive, file_id, dest_path):
    """Download a Drive file to disk."""
    request = drive.files().get_media(fileId=file_id)
    fh = io.FileIO(dest_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.close()
    return Path(dest_path).stat().st_size


def extract_pdf_text(pdf_path):
    """Try pypdf first, then pdfplumber. Returns text."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception as e:
        return f"[EXTRACT_FAIL: {e}]"


def read_sheet(sheets, sheet_id, range_a1):
    resp = sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_a1).execute()
    return resp.get("values", [])


def search_drive(drive, query, page_size=100):
    """Generic Drive search with q expression."""
    items = []
    page_token = None
    while True:
        resp = drive.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, parents, modifiedTime, size)",
            pageSize=page_size,
            pageToken=page_token,
            corpora="user",
            includeItemsFromAllDrives=False,
            supportsAllDrives=False,
        ).execute()
        items.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items
